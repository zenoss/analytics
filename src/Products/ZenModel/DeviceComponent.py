##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""DeviceComponent

All device components inherit from this class

"""

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

import zope.interface
from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import ZEN_VIEW
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Lockable import Lockable
from EventView import EventView
from Products.ZenUtils.Utils import getAllConfmonObjects
from Products.Zuul.catalog.interfaces import IPathReporter
from Products.Zuul.catalog.indexable import ComponentIndexable

class DeviceComponent(Lockable, ComponentIndexable):
    """
    DeviceComponent is a mix-in class for all components of a device.
    These include LogicalComponent, Software, and Hardware.
    """
    zope.interface.implements(IIndexed, IGloballyIdentifiable)
    __pychecker__='no-override'
    event_key = "Component"

    default_catalog = "componentSearch"

    collectors = ('zenperfsnmp', 'zencommand', 'zenwinperf',
                  'zenping')

    security = ClassSecurityInfo()

    perfmonInstance = None

    def getParentDeviceName(self):
        """
        Return the name of this component's device
        """
        name = ""
        dev = self.device()
        if dev: name = dev.getDeviceName()
        return name
    hostname = getParentDeviceName

    def getParentDeviceTitle(self):
        """
        Return the title of this component's device
        """
        title = ""
        dev = self.device()
        if dev: title = dev.titleOrId()
        return title

    def getParentDeviceUrl(self):
        """
        Return the url of this component's device
        """
        url = ""
        dev = self.device()
        if dev: url = dev.absolute_url_path()
        return url

    security.declareProtected(ZEN_VIEW, 'name')
    def name(self):
        """
        Return the name of this component.  Default is id.
        """
        return self.titleOrId()


    def monitored(self):
        """
        Return the monitored status of this component. Default is False.
        """
        return self.monitor


    def getCollectors(self):
        """
        Return list of collectors that want to monitor this component
        """
        return self.collectors


    def getInstDescription(self):
        """
        Return some text that describes this component.  Default is name.
        """
        return self.name()


    def getStatus(self, statClass=None):
        """
        Return the status number for this component of class statClass.
        """
        if not self.monitored() \
            or not self.device() \
            or not self.device().monitorDevice(): return -1
        if not statClass: statClass = "/Status/%s" % self.meta_type
        return EventView.getStatus(self, statClass)

    def getStatusString(self, statClass=None):
        """
        Return a text representation of this component's status
        """
        return self.convertStatus(self.getStatus(statClass=statClass))

    def getManageIp(self):
        """
        Return the manageIP of the device of this component.
        """
        dev = self.device()
        if dev: return dev.getManageIp()
        return ""


    def getNagiosTemplate(self, unused=None):
        import warnings
        warnings.warn('anything named nagios is deprecated', DeprecationWarning)


    def getAqProperty(self, prop):
        """
        Get a property from ourself if it exsits then try serviceclass path.
        """
        if getattr(aq_base(self), prop, None) is not None:
            return getattr(self, prop)
        classObj = self.getClassObject()
        if classObj:
            classObj = classObj.primaryAq()
            return getattr(classObj, prop)


    def setAqProperty(self, prop, value, type):
        """
        Set a local prop if nessesaary on this service.
        """
        classObj = self.getClassObject()
        if not classObj: return
        classObj = classObj.primaryAq()
        svcval = getattr(classObj, prop)
        locval = getattr(aq_base(self),prop,None)
        msg = ""
        if svcval == value and locval is not None:
            self._delProperty(prop)
            msg = "Removed local %s" % prop
        elif svcval != value and locval is None:
            self._setProperty(prop, value, type=type)
            msg = "Set local %s" % prop
        elif locval is not None and locval != value:
            self._updateProperty(prop, value)
            msg = "Update local %s" % prop
        return msg


    def getClassObject(self):
        """
        If you are going to use acquisition up different class path
        override this.
        """
        return self.device()


    def getIconPath(self):
        """
        Get the icon for this component.
        """
        return '/zport/dmd/img/icons/noicon.png'

    def getRRDContextData(self, context):
        context['comp'] = self
        context['compId'] = self.id
        context['compName'] = self.name()
        if self.device():
            context['dev'] = self.device()
            context['devId'] = self.device().id


    def filterAutomaticCreation(self):
        """Test if automatic creation (and anchoring into a model) is
        appropriate for this object.  Lets us ignore detectable gunk
        that's not very interesting to model, like most processes, and
        loopback network devices, CDROM file systems, etc.

        Returns False if the object should not be added.

        The object will have its full acquisition path, but will not
        have been added to the database.
        """
        return True

    def getSubComponentsNoIndexGen(self):
        """Recursively gets every sub component for this component.
        We use the slow method of just looking at every object
        underneath this object and yielding those that are DeviceComponents.

        NOTE: this does not use a catalog and is used only to index a catalog. It
        is painfully inefficient
        @rtype:   generator
        @return:  Every subcomponent directly under this component
        """
        subObjects = getAllConfmonObjects(self)
        for obj in subObjects:
            if isinstance(obj, DeviceComponent):
                yield obj

    def manage_deleteComponent(self, REQUEST=None):
        """
        Delete Component
        """
        url = None
        if REQUEST is not None:
            url = self.device().absolute_url_path()
        self.getPrimaryParent()._delObject(self.id)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)

    def getAllPaths(self):        
        return IPathReporter(self).getPaths()

InitializeClass(DeviceComponent)
