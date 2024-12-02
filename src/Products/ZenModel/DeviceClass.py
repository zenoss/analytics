##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__="""DeviceClass
The primary organizer of device objects, managing zProperties and
their acquisition.
"""

import time
from cStringIO import StringIO
import logging
log = logging.getLogger('zen.DeviceClass')

import DateTime
from zope.event import notify
from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base, aq_chain
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from ZODB.transact import transact

from Products.AdvancedQuery import MatchGlob, Or, Eq, RankByQueries_Max, And
from Products.CMFCore.utils import getToolByName
from Products.ZenMessaging.ChangeEvents.events import DeviceClassMovedEvent
from Products.ZenModel.ZenossSecurity import (
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES,
    ZEN_ADD, ZEN_MANAGE_DMD
)
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenRelations.ZenPropertyManager import Z_PROPERTIES
from Products.ZenUtils.Search import (
   makeCaseInsensitiveFieldIndex,
   makePathIndex, makeMultiPathIndex
)
from Products.ZenUtils.Utils import importClass
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenWidgets import messaging
from Products.ZenUtils.FakeRequest import FakeRequest
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.ZenModel.Exceptions import DeviceExistsError
from Products.Zuul.utils import safe_hasattr as hasattr

import RRDTemplate
from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable
from TemplateContainer import TemplateContainer

_marker = "__MARKER___"

def manage_addDeviceClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = DeviceClass(id, title)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')


addDeviceClass = DTMLFile('dtml/addDeviceClass',globals())


class DeviceClass(DeviceOrganizer, ZenPackable, TemplateContainer):
    """
    DeviceClass is a device organizer that manages the primary classification
    of device objects within the Zenoss system.  It manages properties
    that are inherited through acquisition that modify the behavior of
    many different sub systems within Zenoss.
    It also handles the creation of new devices in the system.
    """

    # Organizer configuration
    dmdRootName = "Devices"

    manageDeviceSearch = DTMLFile('dtml/manageDeviceSearch',globals())
    manageDeviceSearchResults = DTMLFile('dtml/manageDeviceSearchResults',
                                            globals())

    portal_type = meta_type = event_key = "DeviceClass"

    default_catalog = 'deviceSearch'

    _properties = DeviceOrganizer._properties + (
                    {'id':'devtypes', 'type':'lines', 'mode':'w'},
                   )

    _relations = DeviceOrganizer._relations + ZenPackable._relations + \
                TemplateContainer._relations + (
        ("devices", ToManyCont(ToOne,"Products.ZenModel.Device","deviceClass")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'DeviceClass',
            'meta_type'      : 'DeviceClass',
            'description'    : """Base class for all devices""",
            'icon'           : 'DeviceClass_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDeviceClass',
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            (
                { 'name'          : 'Classes'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : ( permissions.view, )
                },
                { 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (  permissions.view, )
                },
                { 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : (permissions.view,)
                },
                { 'name'          : 'Templates'
                , 'action'        : 'perfConfig'
                , 'permissions'   : ('Manage DMD',)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def getPeerDeviceClassNames(self, pyclass=None):
        """
        Return a list of all device paths that have the Python class pyclass

        @param pyclass: Python class (default is this class)
        @type pyclass: Python class
        @return: list of device paths
        @rtype: list of strings
        """
        dcnames = []
        if pyclass == None:
            pyclass = self.getPythonDeviceClass()
        dclass = self.getDmdRoot("Devices")
        for orgname in dclass.getOrganizerNames():
            org = dclass.getOrganizer(orgname)
            if issubclass(org.getPythonDeviceClass(), pyclass):
                dcnames.append(orgname)
        dcnames.sort(key=lambda a: a.lower())
        return dcnames

    deviceMoveTargets = getPeerDeviceClassNames
    childMoveTargets = getPeerDeviceClassNames


    security.declareProtected(ZEN_MANAGE_DMD, 'createInstance')
    def createInstance(self, devId, performanceMonitor="localhost", manageIp=""):
        """
        Create an instance based on its location in the device tree
        walk up the primary aq path looking for a python instance class that
        matches the name of the closest node in the device tree.

        @param devId: id in DMD path
        @type devId: string
        @return: new device object
        @rtype: device object
        """
        devId = self.prepId(devId)
        self._checkDeviceExists(devId, performanceMonitor, manageIp)
        pyClass = self.getPythonDeviceClass()
        dev = pyClass(devId)
        dev.resetProductionState()
        self.devices._setObject(devId, dev)
        devInContext = self.devices._getOb(devId)
        return devInContext

    def _checkDeviceExists(self, deviceName, performanceMonitor, ip):
        if deviceName:
            try:
                dev = self.getDmdRoot('Devices').findDeviceByIdExact(deviceName)
            except Exception:
                pass
            else: 
                if dev:
                    raise DeviceExistsError("Device %s already exists" %
                                            deviceName, dev)
                
        if ip:
            mon = self.getDmdRoot('Monitors').getPerformanceMonitor(performanceMonitor)
            if mon.viewName() != performanceMonitor:
                raise Exception("Collector `{}` does not exist".format(performanceMonitor))
            dev = mon.findDevice(ip)
            if dev:
                raise DeviceExistsError("Manage IP %s already exists" % ip, dev)
        return deviceName, ip

    def getPythonDeviceClass(self):
        """
        Return the Python class object to be used for device instances in this
        device class.  This is done by walking up the aq_chain of a deviceclass
        to find a node that has the same name as a Python class or has an
        attribute named zPythonClass that matches a Python class.

        @return: device class
        @rtype: device class
        """
        from Device import Device
        cname = getattr(self, "zPythonClass", None)
        if cname:
            try:
                return importClass(cname)
            except ImportError:
                log.exception("Unable to import class " + cname)
        return Device

    @transact
    def _moveDevice(self, devname, target, targetClass):
        dev = self.findDeviceByIdExact(devname)
        if not dev:
            return
        guid = IGlobalIdentifier(dev).create()
        source = dev.deviceClass().primaryAq()

        notify(DeviceClassMovedEvent(dev, dev.deviceClass().primaryAq(), target))


        if dev.__class__ != targetClass:
            from Products.ZenRelations.ImportRM import NoLoginImportRM

            def switchClass(o, module, klass):
                """
                Create an XML string representing the module in a
                new class.

                @param o: file-type object
                @type o: file-type object
                @param module: location in DMD
                @type module: string
                @param klass: class name
                @type klass: string
                @return: XML representation of the class
                @rtype: string
                """
                from xml.dom.minidom import parse

                # Note: strips almost everything out of the move
                #       as the new class may not have the same relations etc.
                #       For example, moving SNMP host to a VMware class.
                o.seek(0)
                dom = parse(o)
                root = dom.childNodes[0]
                root.setAttribute('module', module)
                root.setAttribute('class', klass)
                for obj in root.childNodes:
                    if obj.nodeType != obj.ELEMENT_NODE:
                        continue # Keep XML-tree baggage

                    name = obj.getAttribute('id')
                    if obj.tagName == 'property':
                        # Only remove modeler plugins, templates
                        # and z*Ignore zprops
                        if name in ('zCollectorPlugins', 'zDeviceTemplates') or \
                           name.endswith('Ignore'):
                            root.removeChild(obj)

                    elif obj.tagName == 'toone' and \
                         name in ('perfServer', 'location', 'ipaddress'):
                        pass # Preserve collector name, location, and ipaddress

                    elif obj.tagName == 'tomany' and \
                         name in ('systems', 'groups'):
                        pass # Preserve the Groups and Systems groupings

                    elif obj.tagName == 'tomanycont' and \
                         name in ('maintenanceWindows',
                                  'adminRoles',
                                  'userCommands'):
                        pass # Preserve maintenance windows, admins, commands

                    else:
                        log.debug("Removing %s element id='%s'",
                                     obj.tagName, name)
                        root.removeChild(obj)

                importFile = StringIO()
                dom.writexml(importFile)
                importFile.seek(0)
                return importFile

            def devExport(d, module, klass):
                """
                Create an XML string representing the device d
                at the DMD location module of type klass.

                @param module: location in DMD
                @type module: string
                @param klass: class name
                @type klass: string
                @return: XML representation of the class
                @rtype: string
                """
                o = StringIO()
                d.exportXml(o, exportPasswords=True, move=True)
                return switchClass(o, module, klass)

            def devImport(xmlfile):
                """
                Load a new device from a file.

                @param xmlfile: file type object
                @type xmlfile: file type object
                """
                im = NoLoginImportRM(target.devices)
                im.loadObjectFromXML(xmlfile)
                im.processLinks()

            module = target.zPythonClass
            if module:
                klass = target.zPythonClass.split('.')[-1]
            else:
                module = 'Products.ZenModel.Device'
                klass = 'Device'
            log.debug('Exporting device %s from %s', devname, source)
            xmlfile = devExport(dev, module, klass)
            log.debug('Removing device %s from %s', devname, source)
            source.devices._delObject(devname)
            log.debug('Importing device %s to %s', devname, target)
            devImport(xmlfile)
        else:
            dev._operation = 1
            source.devices._delObject(devname)
            target.devices._setObject(devname, dev)
        dev = target.devices._getOb(devname)

        is_dev_moved = True
        IGlobalIdentifier(dev).guid = guid
        dev.setLastChange()
        dev.setAdminLocalRoles()
        notify(IndexingEvent(dev))

        return is_dev_moved

    def moveDevices(self, moveTarget, deviceNames=None, REQUEST=None):
        """
        Override default moveDevices because this is a contained relation.
        If the Python class bound to a DeviceClass is different we convert to
        the new Python class adding / removing relationships as needed.

        @param moveTarget: organizer in DMD path
        @type moveTarget: string
        @param deviceNames: devices to move
        @type deviceNames: list of stringa
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        if not moveTarget or not deviceNames: return self()
        target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
        if isinstance(deviceNames, basestring): deviceNames = (deviceNames,)
        targetClass = target.getPythonDeviceClass()
        moved_devices_count = 0
        for devname in deviceNames:
            devicewasExported = self._moveDevice(devname, target, targetClass)
            if devicewasExported:
                moved_devices_count += 1
        return moved_devices_count

    security.declareProtected(ZEN_DELETE_DEVICE, 'removeDevices')
    def removeDevices(self, deviceNames=None, deleteStatus=False,
                    deleteHistory=False, deletePerf=False,REQUEST=None):
        """
        See IManageDevice overrides DeviceManagerBase.removeDevices
        """
        if not deviceNames: return self()
        if isinstance(deviceNames, basestring): deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.findDevice(devname)
            dev.deleteDevice(deleteStatus=deleteStatus,
                        deleteHistory=deleteHistory, deletePerf=deletePerf)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Devices Deleted',
                "Devices were deleted: %s." % ', '.join(deviceNames)
            )
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return 'Devices were deleted: %s.' % ', '.join(deviceNames)
            else:
                return self.callZenScreen(REQUEST)


    security.declareProtected('View', 'getEventDeviceInfo')
    def getEventDeviceInfo(self):
        """
        getEventDeviceInfo() -> return the info for NcoEventPopulator
        """
        deviceInfo = {}
        for device in self.getSubDevices():
            systemNames = []
            for sys in device.systems.objectValuesAll():
                systemNames.append(sys.getOrganizerName())
            systemNames = "|".join(systemNames)
            location = device.getLocationName()
            if not location: location = "Unknown"
            deviceInfo[device.id] = (systemNames, location,
                                    device.getProductionState(),
                                    device.getDeviceClassPath())
        return deviceInfo


    security.declareProtected('View', 'getDeviceWinInfo')
    def getDeviceWinInfo(self, lastPoll=0, eventlog=False):
        """
        Return list of (devname,user,passwd,url) for each device.
        user and passwd are used to connect via wmi.
        """
        ffunc = None
        starttime = time.time()
        if lastPoll > 0:
            lastPoll = DateTime.DateTime(lastPoll)
            ffunc = lambda x: x.getSnmpLastCollection() > lastPoll
        if eventlog:
            ffunc = lambda x: x.getProperty('zWinEventlog', False)
        devinfo = []
        for dev in self.getSubDevices(devfilter=ffunc):
            if not dev.monitorDevice(): continue
            if dev.getProperty('zWmiMonitorIgnore', False): continue
            user = dev.getProperty('zWinUser','')
            passwd = dev.getProperty( 'zWinPassword', '')
            sev = dev.getProperty( 'zWinEventlogMinSeverity', '')
            devinfo.append((dev.id, str(user), str(passwd), sev, dev.absolute_url_path()))
        return starttime, devinfo


    def getWinServices(self):
        """
        Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0})
        """
        svcinfo = []
        allsvcs = {}
        for s in self.getSubComponents("WinService"):
            svcs=allsvcs.setdefault(s.hostname(),{})
            name = s.name()
            if isinstance(name, unicode):
                name = name.encode(s.zCollectorDecoding)
            svcs[name] = (s.getStatus(), s.getAqProperty('zFailSeverity'))
        for dev in self.getSubDevices():
            if not dev.monitorDevice(): continue
            if dev.getProperty( 'zWmiMonitorIgnore', False): continue
            svcs = allsvcs.get(dev.getId(), {})
            if not svcs and not dev.getProperty('zWinEventlog', False): continue
            user = dev.getProperty('zWinUser','')
            passwd = dev.getProperty( 'zWinPassword', '')
            svcinfo.append((dev.id, str(user), str(passwd), svcs))
        return svcinfo


    security.declareProtected('View', 'searchDeviceSummary')
    def searchDeviceSummary(self, query):
        """
        Search device summary index and return device objects
        """
        # @TODO delete?
        # deviceSearch catalog does not have a summary index nor metadata
        return []


    security.declareProtected('View', 'searchInterfaces')
    def searchInterfaces(self, query):
        """
        Search interfaces index and return interface objects
        """
        if not query: return []
        zcatalog = getattr(self, 'interfaceSearch', None)
        if not zcatalog: return []
        results = zcatalog(query)
        return self._convertResultsToObj(results)


    def _convertResultsToObj(self, results):
        devices = []
        for brain in results:
            try:
                devobj = self.getObjByPath(brain.getPrimaryId)
                devices.append(devobj)
            except KeyError:
                log.warn("bad path '%s' in index", brain.getPrimaryId)

        return devices

    def _findDevice(self, devicename, useTitle=True, commit_dirty=False):
        """
        Returns all devices whose ip/id/title match devicename.
        ip/id matches are at the front of the list.

        @rtype: list of brains
        """
        ors = [ MatchGlob('id', devicename), MatchGlob('text_ipAddress', devicename) ]

        if useTitle:
            ors.append(MatchGlob('name', devicename))

        query = And( Eq("objectImplements", "Products.ZenModel.Device.Device"), Or(*ors) )
        fields = [ "name", "id", "text_ipAddress" ]
        search_results = IModelCatalogTool(self.dmd.Devices).search(query=query, fields=fields, commit_dirty=commit_dirty)
        return list(search_results.results)

    def findDevicePath(self, devicename, commit_dirty=False):
        """
        Look up a device and return its path
        """
        ret = self._findDevice(devicename, commit_dirty=commit_dirty)
        if not ret: return ""
        return ret[0].getPath()

    def findDevice(self, devicename, commit_dirty=False):
        """
        Returns the first device whose ip/id matches devicename.  If
        there is no ip/id match, return the first device whose title
        matches devicename.
        """
        ret = self._findDevice(devicename, commit_dirty=commit_dirty)
        if ret: return ret[0].getObject()

    def findDeviceByIdOrIp(self, devicename, commit_dirty=False):
        """
        Returns the first device that has an ip/id that matches devicename
        """
        ret = self._findDevice( devicename, False, commit_dirty=commit_dirty )
        if ret: return ret[0].getObject()

    def findDeviceByIdExact(self, devicename):
        """
        Look up device in catalog and return it.  devicename
        must match device id exactly
        """
        if devicename:
            query = And( Eq("objectImplements", "Products.ZenModel.Device.Device"), Eq('id', devicename) )
            search_results = IModelCatalogTool(self.dmd.Devices).search(query=query)
            for brain in search_results.results:
                dev = brain.getObject()
                if dev.id == devicename:
                    return dev

    def findDevicePingStatus(self, devicename):
        """
        look up device in catalog and return its pingStatus
        """
        dev = self.findDevice(devicename)
        if dev: return dev.getPingStatusNumber()


    def getSubComponents(self, meta_type="", monitored=True):
        """
        Return generator of components, by meta_type if specified
        """
        catalog = IModelCatalogTool(self)
        COMPONENT = 'Products.ZenModel.DeviceComponent.DeviceComponent'
        monitorq, typeq = None, None
        if monitored:
            monitorq = Eq('monitored', '1')
        if meta_type:
            typeq = Eq('meta_type', meta_type)
        queries = filter(None, (monitorq, typeq))
        if queries:
            query = And(*queries) if len(queries) > 1 else queries[0]
        else:
            query = None
        for brain in catalog.search(COMPONENT, query=query):
            try:
                yield brain.getObject()
            except KeyError:
                log.warn("bad path '%s' in global catalog", brain.getPath())


    security.declareProtected("ZenCommon", "getMonitoredComponents")
    def getMonitoredComponents(self):
        """
        Return monitored components for devices within this DeviceDeviceClass
        """
        return self.getSubComponents()


    security.declareProtected('View', 'getRRDTemplates')
    def getRRDTemplates(self, context=None):
        """
        Return the actual RRDTemplate instances.
        """
        templates = {}
        if not context: context = self
        mychain = aq_chain(context)
        mychain.reverse()
        for obj in mychain:
            try:
                templates.update(dict((t.id, t) for t in obj.rrdTemplates()))
            except AttributeError:
                pass
        return templates.values()


    def getAvailableTemplates(self):
        """
        Returns all available templates
        """
        pdc = self.getPythonDeviceClass()
        templates = filter(lambda t: issubclass(pdc, t.getTargetPythonClass()),
                            self.getRRDTemplates())
        return sorted(templates, key=lambda a: a.id.lower())


    def bindTemplates(self, ids=(), REQUEST=None):
        """
        This will bind available templates to the zDeviceTemplates
        """
        return self.setZenProperty('zDeviceTemplates', ids, REQUEST)

    def removeZDeviceTemplates(self, REQUEST=None):
        """
        Deletes the local zProperty, zDeviceTemplates
        """
        if self.getPrimaryPath()[-2:] == ('dmd', 'Devices'):
            self.setZenProperty('zDeviceTemplates', ['Device'])
        else:
            self.deleteZenProperty('zDeviceTemplates')
        messaging.IMessageSender(self).sendToBrowser(
            'Bindings Reset',
            'Template bindings for this class were reset.'
        )
        return self.callZenScreen(REQUEST)


    def getAllRRDTemplates(self, rrdts=None):
        """
        Return all RRDTemplates at this level and below in the object tree.
        If rrdts is provided then it must be a list of RRDTemplates which
        will be extended with the templates from here and returned.

        The original getAllRRDTemplates() method has been renamed
        getAllRRDTemplatesPainfully().  It walks the object tree looking
        for templates which is a very slow way of going about things.
        The newer RRDTemplate.YieldAllRRDTemplate() method uses the
        searchRRDTemplates catalog to speed things up dramatically.
        YieldAllRRDTemplates is smart enough to revert to
        getAllRRDTemplatesPainfully if the catalog is not present.

        The searchRRDTemplates catalog was added in 2.2
        """
        if rrdts is None:
            rrdts = []
        rrdts.extend(RRDTemplate.YieldAllRRDTemplates(self))
        return rrdts


    def getAllRRDTemplatesPainfully(self, rrdts=None):
        """
        RRDTemplate.YieldAllRRDTemplates() is probably what you want.
        It takes advantage of the searchRRDTemplates catalog to get
        much better performance.  This method iterates over objects looking
        for templates which is a slow, painful process.
        """
        if rrdts is None: rrdts = []
        rrdts.extend(self.rrdTemplates())
        for dev in self.devices():
            rrdts += dev.objectValues('RRDTemplate')
            for comps in dev.getDeviceComponents():
                rrdts += comps.objectValues('RRDTemplate')
        for child in self.children():
            child.getAllRRDTemplatesPainfully(rrdts)
        return rrdts


    security.declareProtected('Add DMD Objects', 'manage_addRRDTemplate')
    def manage_addRRDTemplate(self, id, REQUEST=None):
        """
        Add an RRDTemplate to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        id = self.prepId(id)
        org = RRDTemplate.RRDTemplate(id)
        self.rrdTemplates._setObject(org.id, org)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Template Added',
                'The "%s" template has been created.' % id
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_copyRRDTemplates')
    def manage_copyRRDTemplates(self, ids=(), REQUEST=None):
        """
        Put a reference to the objects named in ids in the clip board
        """
        if not ids: return self.callZenScreen(REQUEST)
        ids = [ id for id in ids if self.rrdTemplates._getOb(id, None) is not None]
        if not ids: return self.callZenScreen(REQUEST)
        cp = self.rrdTemplates.manage_copyObjects(ids)
        if REQUEST:
            resp=REQUEST['RESPONSE']
            resp.setCookie('__cp', cp, path='/zport/dmd')
            REQUEST['__cp'] = cp
            messaging.IMessageSender(self).sendToBrowser(
                'Templates Copied',
                'Templates have been copied: %s' % ', '.join(ids)
            )
            return self.callZenScreen(REQUEST)
        return cp


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_pasteRRDTemplates')
    def manage_pasteRRDTemplates(self, moveTarget=None, cb_copy_data=None, REQUEST=None):
        """
        Paste RRDTemplates that have been copied before.
        """
        cp = None
        if cb_copy_data: cp = cb_copy_data
        elif REQUEST:
            cp = REQUEST.get("__cp",None)

        if cp:
            if moveTarget:
                target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
            else:
                target = self
            target.rrdTemplates.manage_pasteObjects(cp)
        else:
            target = None

        if REQUEST:
            REQUEST['RESPONSE'].setCookie('__cp', 'deleted', path='/zport/dmd',
                            expires='Wed, 31-Dec-97 23:59:59 GMT')
            REQUEST['__cp'] = None
            if target:
                message = "Template(s) copied to %s" % moveTarget
            else:
                message = None
            messaging.IMessageSender(self).sendToBrowser(
                'Template(s) Copied',
                message
            )
            if not isinstance(REQUEST, FakeRequest):
                url = target.getPrimaryUrlPath() + '/perfConfig'
                if message:
                    url += '?message=%s' % message
                REQUEST['RESPONSE'].redirect(url)
            else:
                return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_copyAndPasteRRDTemplates')
    def manage_copyAndPasteRRDTemplates(self, ids=(), copyTarget=None, REQUEST=None):
        """
        Copy the selected templates into the specified device class.
        """
        if not ids:
            messaging.IMessageSender(self).sendToBrowser(
                'Invalid',
                'No templates were selected.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        if copyTarget is None:
            messaging.IMessageSender(self).sendToBrowser(
                'Invalid',
                'No target was selected.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        cp = self.manage_copyRRDTemplates(ids)
        return self.manage_pasteRRDTemplates(copyTarget, cp, REQUEST)


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_deleteRRDTemplates')
    def manage_deleteRRDTemplates(self, ids=(), paths=(), REQUEST=None):
        """
        Delete RRDTemplates from this DeviceClass
        (skips ones in other Classes)
        """
        if not ids and not paths:
            return self.callZenScreen(REQUEST)
        for id in ids:
            if (getattr(aq_base(self), 'rrdTemplates', False)
                and getattr(aq_base(self.rrdTemplates),id,False)):
                self.rrdTemplates._delObject(id)
        for path in paths:
            temp = self.dmd.getObjByPath(path)
            if temp.deviceClass():
                temp.deviceClass().rrdTemplates._delObject(temp.id)
            else:
                temp.device()._delObject(temp.id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Templates Deleted',
                'Templates were deleted: %s' % ", ".join(ids)
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ADD, 'createCatalog')
    def createCatalog(self):
        """
        Make the catalog for device searching.
        deviceSearch catalog is deprecated.
        """
        from Products.Zuul.catalog.legacy import LegacyCatalogAdapter
        if hasattr(self, self.default_catalog):
            self._delObject(self.default_catalog)
        setattr(self, self.default_catalog, LegacyCatalogAdapter(self, self.default_catalog))

    security.declareProtected(ZEN_MANAGE_DMD, 'reIndex')
    def reIndex(self):
        """
        Go through all devices in this tree and reindex them.
        """
        for dev in self.getSubDevicesGen_recursive():
            if dev.hasObject('componentSearch'):
                dev._delObject('componentSearch')
            dev._create_componentSearch()
            notify(IndexingEvent(dev))
            for comp in dev.getDeviceComponentsNoIndexGen():
                notify(IndexingEvent(comp))

    def buildDeviceTreeProperties(self):
        """
        Create a new device tree with a default configuration
        """
        devs = self.getDmdRoot("Devices")
        for item in Z_PROPERTIES:
            id = item[0]
            defaultValue = item[1]            
            type = item[2]
            if not devs.hasProperty(id):
                devs._setProperty(id, defaultValue, type)

    def pushConfig(self, REQUEST=None):
        """
        This will result in a push of all the devices to live collectors

        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        self._p_changed = True
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Pushed Changes',
                'Changes to %s were pushed to collectors.' % self.id
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setLastChange')
    def setLastChange(self, value=None):
        """
        Set the changed datetime for this device.

        @param value: changed datetime. Default is now.
        @type value: number
        """
        if value is None:
            value = time.time()
        self._lastChange = float(value)

    def register_devtype(self, description, protocol):
        """
        Define this class in terms of a description of the devices it should
        contain and the protocol by which they would normally be monitored.
        """
        t = (description, protocol)
        if not self.isLocal('devtypes'):
            self._setProperty('devtypes', [], 'lines')
        if t not in self.devtypes:
            self.devtypes.append(t)
            self._p_changed = True

    def unregister_devtype(self, description, protocol):
        t = (description, protocol)
        if hasattr(self, 'devtypes'):
            if t in self.devtypes:
                self.devtypes.remove(t)
                self._p_changed = True


InitializeClass(DeviceClass)
