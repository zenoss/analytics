##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """ZDeviceLoader.py

load devices from a GUI screen in the ZMI

"""

import socket
from logging import StreamHandler, Formatter, getLogger

log = getLogger("zen.DeviceLoader")

from ipaddr import IPAddress

import transaction
from zope.interface import implements
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from DateTime import DateTime
from OFS.SimpleItem import SimpleItem

from Products.Jobber.zenjobs import app
from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader
from Products.ZenUtils.Utils import clearWebLoggingStream
from Products.ZenUtils.IpUtil import getHostByName, ipwrap

from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenModel.Exceptions import DeviceExistsError, NoSnmp
from Products.ZenModel.Device import manage_createDevice
from Products.ZenWidgets import messaging
from Products.Jobber.jobs import Job
from ZenModelItem import ZenModelItem
from zExceptions import BadRequest
from Products.ZenModel.interfaces import IDeviceLoader
from ZenossSecurity import ZEN_CHANGE_DEVICE


def manage_addZDeviceLoader(context, id="", REQUEST=None):
    """
    Make a DeviceLoader.
    """
    if not id:
        id = "DeviceLoader"
    d = ZDeviceLoader(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     + '/manage_main')


class BaseDeviceLoader(object):
    implements(IDeviceLoader)

    context = None
    request = None
    deviceobj = None

    def __init__(self, context):
        self.context = context

    def run_zendisc(self, deviceName, devicePath, performanceMonitor,
                    productionState):
        """
        Various ways of doing this should be implemented in subclasses.
        """
        raise NotImplementedError

    def cleanup(self):
        """
        Delete the device object, presumably because discovery failed.
        """
        if self.deviceobj is not None:
            try:
                self.deviceobj._p_jar.sync()
            except AttributeError:
                pass
            else:
                if self.deviceobj.isTempDevice():
                    # Flag's still True, so discovery failed somehow.
                    # Clean up the device object.
                    self.deviceobj.deleteDevice(True, True, True)
                    self.deviceobj = None

    def load_device(self, deviceName, devicePath='/Discovered',
                    discoverProto='snmp', performanceMonitor='localhost',
                    manageIp="", zProperties=None, deviceProperties=None):
        """
        Load a single device into the database.
        """
        # Make the config dictionaries the proper type
        try:
            if zProperties is None:
                zProperties = {}
            if deviceProperties is None:
                deviceProperties = {}

            # Remove spaces from the name
            deviceName = deviceName.replace(' ', '')
            manageIp = manageIp.replace(' ', '')

            if not manageIp:
                try:
                    IPAddress(deviceName)
                    manageIp = deviceName
                    deviceName = ipwrap(deviceName)
                    deviceProperties.setdefault('title', manageIp)
                except ValueError:
                    pass

            # If we're not discovering and we have no IP, attempt the IP lookup
            # locally
            if discoverProto == 'none' and not manageIp:
                try:
                    manageIp = getHostByName(deviceName)
                except socket.error:
                    pass

            # move the zProperties required by manage_createDevice to
            # deviceProperties
            for key in 'zSnmpCommunity', 'zSnmpPort', 'zSnmpVer':
                if key in zProperties:
                    deviceProperties[key] = zProperties.pop(key)

            # Make a device object in the database
            self.deviceobj = manage_createDevice(
                self.context, deviceName, devicePath,
                performanceMonitor=performanceMonitor, manageIp=manageIp,
                zProperties=zProperties, **deviceProperties
            )

            # Flag this device as temporary.
            # If discovery goes well, zendisc will flip this to False.
            self.deviceobj._temp_device = True

            # If we're not discovering, we're done
            if discoverProto == 'none':
                return self.deviceobj

            # Pass production state from device properties
            productionState = deviceProperties.get('productionState', 1000)

            # Otherwise, time for zendisc to do its thing
            self.run_zendisc(deviceName, devicePath, performanceMonitor,
                             productionState)

        finally:
            # Check discovery's success and clean up accordingly
            self.cleanup()

        return self.deviceobj


class JobDeviceLoader(BaseDeviceLoader):
    implements(IDeviceLoader)

    def run_zendisc(self, deviceName, devicePath, performanceMonitor,
                    productionState):
        """
        In this subclass, just commit to database,
        so everybody can find the new device
        """
        pass

    def cleanup(self):
        """
        Delegate cleanup to the Job itself.
        """
        pass


class CreateDeviceJob(Job):
    """
    Create a new device object.
    """
    name = 'CreateDeviceJob'
    # Declare DeviceExistsError as an expected exception so that a traceback
    # is not written to zenjobs' log.
    throws = Job.throws + (DeviceExistsError,)

    @classmethod
    def getJobType(cls):
        return "Create Device"

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        return "Create %(name)s under %(path)s" % {
            'name': args[0], 'path': kwargs.get('devicePath')
        }

    def _run(self, deviceName, devicePath="/Discovered", tag="",
             serialNumber="", rackSlot=0, productionState=1000, comments="",
             hwManufacturer="", hwProductName="", osManufacturer="",
             osProductName="", locationPath="", groupPaths=[], systemPaths=[],
             performanceMonitor="localhost", discoverProto="snmp", priority=3,
             manageIp="", zProperties=None, cProperties=None, title="",
             zendiscCmd=[]):
        """
        Returns the 'physical' path of the device.
        """
        loader = JobDeviceLoader(self.dmd)
        deviceProps = dict(tag=tag,
                           serialNumber=serialNumber,
                           rackSlot=rackSlot,
                           productionState=productionState,
                           comments=comments,
                           hwManufacturer=hwManufacturer,
                           hwProductName=hwProductName,
                           osManufacturer=osManufacturer,
                           osProductName=osProductName,
                           locationPath=locationPath,
                           groupPaths=groupPaths,
                           systemPaths=systemPaths,
                           priority=priority,
                           title=title)

        def createDevice():
            # set the status properties that were modified up until this
            # point in case of a Conflict Error
            self.setProperties(**zProperties)
            self.setProperties(**deviceProps)
            # create the device
            return loader.load_device(
                deviceName, devicePath, discoverProto,
                performanceMonitor, manageIp, zProperties, deviceProps
            )

        try:
            device = createDevice()

            # Now set the custom properties
            if cProperties is not None:
                for prop, value in cProperties.items():
                    self.setCustomProperty(device, prop, value)

            return '/'.join(device.getPhysicalPath())
        except DeviceExistsError as e:
            transaction.abort()
            # If the device already exists, log it and raise exception.
            self.log.error(
                "Device already exists (job was likely interrupted "
                "and restarted): %s", e
            )
            raise
        except Exception:
            transaction.abort()
            self.log.exception("Failed to create device.")
            raise

    def setCustomProperty(self, dev, cProperty, value):
        # make sure it is the correct type
        ztype = dev.getPropertyType(cProperty)
        if ztype == 'int':
            value = int(value)
        if ztype == 'float':
            value = float(value)
        if ztype == 'string':
            value = str(value)
        if ztype == 'date':
            value = value.replace('%20', ' ')  # Ugh. Manually decode spaces
            value = DateTime(value)
        # do not save * as passwords
        if dev.zenPropIsPassword(cProperty) \
                and value == dev.zenPropertyString(cProperty):
            return
        return dev.setZenProperty(cProperty, value)


app.register_task(CreateDeviceJob)
# alias the DeviceCreationJob so zenpacks don't break
DeviceCreationJob = CreateDeviceJob


class WeblogDeviceLoader(BaseDeviceLoader):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def run_zendisc(self, deviceName, devicePath, performanceMonitor,
                    productionState):
        # Commit to database so everybody can find the new device
        transaction.commit()
        collector = self.deviceobj.getPerformanceServer()
        collector._executeZenDiscCommand(deviceName, devicePath,
                                         performanceMonitor, productionState,
                                         REQUEST=self.request)


class ZDeviceLoader(ZenModelItem, SimpleItem):
    """Load devices into the DMD database"""

    portal_type = meta_type = 'DeviceLoader'

    manage_options = (
        ({'label': 'ManualDeviceLoader', 'action': 'manualDeviceLoader'},)
        + SimpleItem.manage_options
    )

    security = ClassSecurityInfo()

    factory_type_information = ({
        'immediate_view': 'addDevice',
        'actions': ({
            'id':          'status',
            'name':        'Status',
            'action':      'addDevice',
            'permissions': (permissions.view,)
        },)
    },)

    def __init__(self, id):
        self.id = id

    def loadDevice(self, deviceName, devicePath="/Discovered",
                   tag="", serialNumber="",
                   zSnmpCommunity="", zSnmpPort=161, zSnmpVer=None,
                   rackSlot=0, productionState=1000, comments="",
                   hwManufacturer="", hwProductName="",
                   osManufacturer="", osProductName="",
                   locationPath="", groupPaths=[], systemPaths=[],
                   performanceMonitor="localhost", manageIp="",
                   discoverProto="snmp", priority=3, title=None, REQUEST=None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration.
        """
        device = None
        if not deviceName:
            return self.callZenScreen(REQUEST)
        xmlrpc = isXmlRpc(REQUEST)
        if REQUEST and not xmlrpc:
            handler = setupLoggingHeader(self, REQUEST)

        loader = WeblogDeviceLoader(self, REQUEST)

        try:
            device = loader.load_device(deviceName, devicePath, discoverProto,
                                        performanceMonitor,
                                        manageIp,
                                        zProperties=dict(
                                            zSnmpCommunity=zSnmpCommunity,
                                            zSnmpPort=zSnmpPort,
                                            zSnmpVer=zSnmpVer
                                        ),
                                        deviceProperties=dict(
                                            tag=tag,
                                            serialNumber=serialNumber,
                                            rackSlot=rackSlot,
                                            productionState=productionState,
                                            comments=comments,
                                            hwManufacturer=hwManufacturer,
                                            hwProductName=hwProductName,
                                            osManufacturer=osManufacturer,
                                            osProductName=osProductName,
                                            locationPath=locationPath,
                                            groupPaths=groupPaths,
                                            systemPaths=systemPaths,
                                            priority=priority,
                                            title=title
                                        ))
        except ZentinelException as e:
            log.info(e)
            if xmlrpc:
                return 1
        except DeviceExistsError as e:
            log.info(e)
            if xmlrpc:
                return 2
        except NoSnmp as e:
            log.info(e)
            if xmlrpc:
                return 3
        except Exception as e:
            log.exception(e)
            log.exception('load of device %s failed', deviceName)
            transaction.abort()
        if device is None:
            log.error("Unable to add the device %s", deviceName)
        else:
            log.info("Device %s loaded!", deviceName)

        if REQUEST and not xmlrpc:
            self.loaderFooter(device, REQUEST.RESPONSE)
            clearWebLoggingStream(handler)
        if xmlrpc:
            return 0

    security.declareProtected(ZEN_CHANGE_DEVICE, 'addManufacturer')
    def addManufacturer(self, newHWManufacturerName=None,
                        newSWManufacturerName=None, REQUEST=None):
        """
        Add a manufacturer to the database.
        """
        mname = newHWManufacturerName
        field = 'hwManufacturer'
        if not mname:
            mname = newSWManufacturerName
            field = 'osManufacturer'
        try:
            self.getDmdRoot("Manufacturers").createManufacturer(mname)
        except BadRequest as e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e

        if REQUEST:
            REQUEST[field] = mname
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setHWProduct')
    def setHWProduct(self, newHWProductName, hwManufacturer, REQUEST=None):
        """
        Set the productName of this device.
        """
        if not hwManufacturer and REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'Please select a HW Manufacturer',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        self.getDmdRoot("Manufacturers").createHardwareProduct(
            newHWProductName, hwManufacturer)
        if REQUEST:
            REQUEST['hwProductName'] = newHWProductName
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setOSProduct')
    def setOSProduct(self, newOSProductName, osManufacturer, REQUEST=None):
        """
        Set the productName of this device.
        """
        if not osManufacturer and REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'Please select an OS Manufacturer.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        self.getDmdRoot("Manufacturers").createSoftwareProduct(
            newOSProductName, osManufacturer, isOS=True)
        if REQUEST:
            REQUEST['osProductName'] = newOSProductName
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'addLocation')
    def addLocation(self, newLocationPath, REQUEST=None):
        """
        Add a location to the database.
        """
        try:
            self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        except BadRequest as e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e

        if REQUEST:
            REQUEST['locationPath'] = newLocationPath
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """
        Add a system to the database.
        """
        try:
            self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        except BadRequest as e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e

        syss = REQUEST.get('systemPaths', [])
        syss.append(newSystemPath)
        if REQUEST:
            REQUEST['systemPaths'] = syss
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """
        Add a device group to the database.
        """
        try:
            self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        except BadRequest as e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e

        groups = REQUEST.get('groupPaths', [])
        groups.append(newDeviceGroupPath)
        if REQUEST:
            REQUEST['groupPaths'] = groups
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setPerformanceMonitor')
    def setPerformanceMonitor(self, newPerformanceMonitor, REQUEST=None):
        """
        Add new performance monitor to the database.
        """
        try:
            self.getDmdRoot("Monitors").setPerformanceMonitor(
                newPerformanceMonitor)
        except BadRequest as e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e
        if REQUEST:
            REQUEST['performanceMonitor'] = newPerformanceMonitor
            return self.callZenScreen(REQUEST)

    def setupLog(self, response):
        """
        Setup logging package to send to browser.
        """
        root = getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)

    def clearLog(self):
        alog = getLogger()
        if getattr(self, "_v_handler", False):
            alog.removeHandler(self._v_handler)

    def loaderFooter(self, devObj, response):
        """
        Add navigation links to the end of the loader output.
        """
        if not devObj:
            return
        devurl = devObj.absolute_url_path()
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to device <a href=%s>%s</a></td></tr>"""
                       % (devurl, devObj.getId()))
        response.write("</table></body></html>")
