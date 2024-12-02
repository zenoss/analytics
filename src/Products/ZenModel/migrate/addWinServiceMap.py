##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Acquisition import aq_base

class addWinServiceMap(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        try:
            win = dmd.Devices.getOrganizer("/Server/Windows")
            if not hasattr(aq_base(win),'zCollectorPlugins'):
                win._setProperty("zCollectorPlugins", 
                    (
                        'zenoss.snmp.NewDeviceMap',
                        'zenoss.snmp.DeviceMap',
                        'zenoss.snmp.DellDeviceMap',
                        'zenoss.snmp.HPDeviceMap',
                        'zenoss.snmp.InterfaceMap',
                        'zenoss.snmp.RouteMap',
                        'zenoss.snmp.IpServiceMap',
                        'zenoss.snmp.HRFileSystemMap',
                        'zenoss.snmp.HRSWInstalledMap',
                        'zenoss.snmp.HRSWRunMap',
                        'zenoss.snmp.CpuMap',
                        'zenoss.snmp.DellCPUMap',
                        'zenoss.snmp.DellPCIMap',
                        'zenoss.snmp.HPCPUMap',
                        'zenoss.snmp.InformantHardDiskMap',
                        'zenoss.wmi.WinServiceMap'
                    ), type = 'lines')
            else:
                if 'zenwin.wmi.WinServiceMap' in win.zCollectorPlugins:
                    win.zCollectorPlugins.remove('zenwin.wmi.WinServiceMap')
                if 'zenoss.wmi.WinServiceMap' not in win.zCollectorPlugins:
                    win.zCollectorPlugins += ('zenoss.wmi.WinServiceMap',)
        except Exception: pass

addWinServiceMap()
