##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

from Products.ZenModel.DeviceClass import manage_addDeviceClass

class TwoPointOhObjects(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def ignoreMissing(self, function, *args):
        try:
            function(*args)
        except AttributeError:
            pass

    def cutover(self, dmd):
        self.ignoreMissing(self._loopback, dmd)
        self.ignoreMissing(self._zCommandPath, dmd)
        self.ignoreMissing(self._cleanupClass, dmd)
        self.ignoreMissing(self._cmdClass, dmd)
        self.ignoreMissing(self._pingClass, dmd)
        self.ignoreMissing(self._scanClass, dmd)
        self.ignoreMissing(self._eventClasses, dmd)


    def _loopback(self, dmd):
        dmd.Devices.manage_addRRDTemplate('softwareLoopback')

    def _zCommandPath(self, dmd):
        from Products.ZenUtils.path import zenPath
        dmd.Devices.zCommandPath = zenPath('libexec')

    def _cleanupClass(self, dmd):
        d = [d.id for d in dmd.Devices.Server.Linux.getSubDevices()]
        if d: dmd.Devices.moveDevices('/Server/Linux', d)
        for name in ['RedHat', 'Ubuntu']:
            if getattr(dmd.Devices.Server.Linux, name, False):
                dmd.Devices.Server.Linux.manage_deleteOrganizers([name])

    def _cmdClass(self, dmd):
        if not hasattr(dmd.Devices.Server, 'Cmd'):
            manage_addDeviceClass(dmd.Devices.Server, 'Cmd')
            cmd = dmd.Devices.Server.Cmd
            cmd.description = ''
            cmd.zPingMonitorIgnore = True
            cmd.zSnmpMonitorIgnore = True
            cmd.zWmiMonitorIgnore = True
            cmd.zXmlRpcMonitorIgnore = True
            cmd.manage_addRRDTemplate('Device')
            
        
    def _pingClass(self, dmd):
        if not hasattr(dmd.Devices, 'Ping'):
            manage_addDeviceClass(dmd.Devices, 'Ping')
            ping = dmd.Devices.Server.Ping
            ping.description = ''
            ping.zSnmpMonitorIgnore = True
            ping.zXmlRpcMonitorIgnore = True
            ping.manage_addRRDTemplate('Device')
            
        
    def _scanClass(self, dmd):
        if not hasattr(dmd.Devices.Server, 'Scan'):
            manage_addDeviceClass(dmd.Devices.Server, 'Scan')
            scan = dmd.Devices.Server.Scan
            scan.description = ''
            scan.zCollectorPlugins = ['zenoss.portscan.IpServiceMap']
            scan.manage_addRRDTemplate('Device')
            
        
    def _eventClasses(self, dmd):
        from Products.ZenEvents.EventClass import manage_addEventClass
        from Products.ZenEvents import ZenEventClasses
        for evt in dir(ZenEventClasses):
            val = getattr(ZenEventClasses, evt, '')
            if type(val) != type('') or val.find('/') != 0:
                    continue
            root = dmd.Events
            for elt in val.split('/')[1:]:
                try:
                    manage_addEventClass(root, elt)
                    cls = root._getOb(elt)
                    if elt == 'Blocked':
                        cls.zEventSeverity = ZenEventClasses.Warning
                        cls.zEventAction = 'status'
                    elif val == "/Change":
                        cls.zEventAction = 'history'
                except Exception as ex:
                    pass
                root = root._getOb(elt)
        


TwoPointOhObjects()
