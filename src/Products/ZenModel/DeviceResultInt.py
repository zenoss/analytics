##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""DeviceResult

A mixin for objects that get listed like devices
The primary object must implement device.

"""


from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from cgi import escape

class DeviceResultInt:

    security = ClassSecurityInfo()

    security.declareProtected('View', 'getDeviceName')
    def getDeviceName(self):
        '''Get the id of this device or associated device'''
        d = self.device()
        if d:
            return d.getId()
        return "No Device"


    security.declareProtected('View', 'getDeviceUrl')
    def getDeviceUrl(self):
        '''Get the primary url path of the device in which this
        interface is located'''
        d = self.device()
        if d:
            return d.getPrimaryUrlPath()
        return ""


    security.declareProtected('View', 'getDeviceLink')
    def getDeviceLink(self, screen=""):
        '''Get the primary link for the device'''
        d = self.device()
        if d:
            if self.checkRemotePerm("View", d):
                return "<a href='%s/%s'>%s</a>" % (
                    d.getPrimaryUrlPath(), screen, escape(d.titleOrId()))
            else:
                return d.getId()
        return ""


    security.declareProtected('View', 'getDeviceClassPath')
    def getDeviceClassPath(self):
        '''Get the device class name for this device'''
        d = self.device()
        if d:
            return d.deviceClass().getOrganizerName()
        return "No Device"
    security.declareProtected('View', 'getDeviceClassName')
    getDeviceClassName = getDeviceClassPath


    security.declareProtected('View', 'getProdState')
    def getProdState(self):
        '''Get the production state of the device associated with
        this interface'''
        d = self.device()
        if d:
            # since this method is used as a case-insensitive index
            # always return a string
            return str(self.convertProdState(d.getProductionState()))
        return "None"


    security.declareProtected('View', 'getDeviceStatus')
    def getDeviceStatus(self):
        dev = self.device()
        if dev:
            dev = dev.primaryAq()
            return dev.getStatus()
        else:
            return self.getStatus()
        return -1


    security.declareProtected('View', 'getPingStatus')
    def getPingStatus(self):
        """get the ping status of the box if there is one"""
        # this import must be deferred to this point to avoid circular imports
        from Products.ZenEvents.ZenEventClasses import Status_Ping
        dev = self.device()
        if dev:
            dev = dev.primaryAq()
            return dev.getStatus(Status_Ping)
        else:
            return self.getStatus(Status_Ping)
        return -1
    security.declareProtected('View', 'getPingStatusNumber')
    getPingStatusNumber = getPingStatus


    security.declareProtected('View', 'getSnmpStatus')
    def getSnmpStatus(self):
        """get the snmp status of the box if there is one"""
        # this import must be deferred to this point to avoid circular imports
        __pychecker__='no-shadow'
        from Products.ZenEvents.ZenEventClasses import Status_Snmp
        dev = self.device()
        if dev:
            dev = dev.primaryAq()
            if (not getattr(dev, 'zSnmpMonitorIgnore', False)
                and getattr(dev, 'zSnmpCommunity', "")
                and dev.monitorDevice()):
                return dev.getStatus(Status_Snmp)
        return -1
    getSnmpStatusNumber = getSnmpStatus
    security.declareProtected('View', 'getSnmpStatusNumber')


    security.declareProtected('View', 'isResultLockedFromUpdates')
    def isResultLockedFromUpdates(self):
        """Return the locked from updates flag"""
        d = self.device()
        if d:
            return d.isLockedFromUpdates()
        return False

    security.declareProtected('View', 'isResultLockedFromDeletion')
    def isResultLockedFromDeletion(self):
        """Return the locked from deletion flag"""
        d = self.device()
        if d:
            return d.isLockedFromDeletion()
        return False

    security.declareProtected('View', 'sendEventWhenResultBlocked')
    def sendEventWhenResultBlocked(self):
        """Return the send event flag"""
        d = self.device()
        if d:
            return d.sendEventWhenBlocked()
        return False


    security.declareProtected('View', 'getDeviceIp')
    def getDeviceIp(self):
        """Get the management ip (only) of a device"""
        d = self.device()
        if d:
            return d.manageIp
        return ""


    security.declareProtected('View', 'getDeviceIpAddress')
    def getDeviceIpAddress(self):
        """Get the management ip with netmask (1.1.1.1/24) of a device"""
        d = self.device()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getIpAddress()
        return ""


    security.declareProtected('View', 'getDeviceMacaddress')
    def getDeviceMacaddress(self):
        """get the mac address if there is one of the primary interface"""
        d = self.device()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getInterfaceMacaddress()
        return ""

    security.declareProtected('View', 'getNonLoopbackIpAddresses')
    def getNonLoopbackIpAddresses(self, showNetMask=False):
        """
        List the IP addresses to which we can contact the service.
        Discards the loopback (127.0.0.1) address.
        By default do not show the netmasks.

        @parameter showNetMask: return IP addresses with netmasks?
        @type showNetMask: Boolean
        @return: list of IP addresses
        @rtype: array of strings
        """
        ip_list = []
        dev = self.device()
        if dev:
            ip_list = ( obj.getIpAddress()
                         for obj in dev.os.interfaces.objectValuesAll() )
            ip_list = [ ip for ip in ip_list if ip and \
                         not ip.startswith('127.0.0.1') and \
                         not ip.startswith('::1')]
        else:
            manage_ip = self.getDeviceIp()
            if manage_ip:
                ip_list = [ manage_ip ]

        if not showNetMask:
            ip_list = [ ip.split('/',1)[0] for ip in ip_list ]

        return ip_list


InitializeClass(DeviceResultInt)
