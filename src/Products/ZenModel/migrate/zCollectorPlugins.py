#!!!!!!!! No /Server class we have nothing more to do. !!!!!!!!!!!!!!
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
from Products.ZenModel.DeviceClass import DeviceClass

class zCollectorPlugins(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):

        if not hasattr(aq_base(dmd.Devices), 'zCollectorPlugins'):
            dmd.Devices._setProperty("zCollectorPlugins", (), type='lines')

        if not dmd.Devices.zCollectorPlugins:
            dmd.Devices.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
                    'zenoss.snmp.DeviceMap',
                    'zenoss.snmp.InterfaceMap',
                    'zenoss.snmp.RouteMap',
                )

        try:
            pow = dmd.Devices.getOrganizer("/Power")
            if not hasattr(aq_base(pow),'zCollectorPlugins'):
                pow._setProperty("zCollectorPlugins", 
                    (
                        'zenoss.snmp.NewDeviceMap',
                        'zenoss.snmp.DeviceMap',
                        'zenoss.snmp.APCDeviceMap',
                        'zenoss.snmp.PowerwareDeviceMap',
                    ), type = 'lines')
        except KeyError: pass

        try:
            rc = dmd.Devices.getOrganizer("/Network/Router/Cisco")
            if not hasattr(aq_base(rc),'zCollectorPlugins'):
                rc._setProperty('zCollectorPlugins',
                    (
                        'zenoss.snmp.NewDeviceMap',
                        'zenoss.snmp.DeviceMap',
                        'zenoss.snmp.CiscoMap',
                        'zenoss.snmp.InterfaceMap',
                        'zenoss.snmp.CiscoHSRP',
                        'zenoss.snmp.RouteMap',
                    ), type = 'lines')
        except Exception: pass

        try:
            
            serv = dmd.Devices.getOrganizer("/Server")
            if not hasattr(aq_base(serv),'zCollectorPlugins'):
                serv._setProperty("zCollectorPlugins", 
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
                        'zenoss.snmp.HPCPUMap',
                        'zenoss.snmp.DellPCIMap',
                    ), type = 'lines')
        except KeyError: 
            return

        # Setup the /Server/Scan class
        if not dmd.Devices.Server._getOb('Scan',False):
            scan = DeviceClass('Scan')
            dmd.Devices.Server._setObject('Scan',scan)
        if not hasattr(aq_base(dmd.Devices.Server.Scan), 'zCollectorPlugins'):
            dmd.Devices.Server.Scan._setProperty("zCollectorPlugins", 
                (
                    'zenoss.portscan.IpServiceMap',
                ), type = 'lines')
        if not hasattr(aq_base(dmd.Devices.Server.Scan), 'zSnmpMonitorIgnore'):
            dmd.Devices.Server.Scan._setProperty(
                    "zSnmpMonitorIgnore", True, type='boolean')
       
        # Setup the /Server/Cmd class
        if not dmd.Devices.Server._getOb('Cmd',False):
            cmd = DeviceClass('Cmd')
            dmd.Devices.Server._setObject('Cmd', cmd)
        if not hasattr(aq_base(dmd.Devices.Server.Cmd), 'zCollectorPlugins'):
            dmd.Devices.Server.Cmd._setProperty("zCollectorPlugins", 
                (
                    'zenoss.cmd.uname',
                    'zenoss.cmd.df',
                    'zenoss.cmd.linux.ifconfig',
                    'zenoss.cmd.linux.memory',
                    'zenoss.cmd.linux.netstat_an',
                    'zenoss.cmd.linux.netstat_rn',
                    'zenoss.cmd.linux.process',
                    'zenoss.cmd.darwin.cpu',
                    'zenoss.cmd.darwin.ifconfig',
                    'zenoss.cmd.darwin.memory',
                    'zenoss.cmd.darwin.netstat_an',
                    'zenoss.cmd.darwin.process',
                    'zenoss.cmd.darwin.swap',
                ), type = 'lines')
        if not hasattr(aq_base(dmd.Devices.Server.Cmd), 'zSnmpMonitorIgnore'):
            dmd.Devices.Server.Cmd._setProperty(
                    "zSnmpMonitorIgnore", True, type='boolean')

        try:
            lin = dmd.Devices.getOrganizer("/Server/Linux")
            if not hasattr(aq_base(lin), 'zCollectorPlugins'):
                lin._setProperty("zCollectorPlugins", 
                    (
                        'zenoss.snmp.NewDeviceMap',
                        'zenoss.snmp.DeviceMap',
                        'zenoss.snmp.DellDeviceMap',
                        'zenoss.snmp.HPDeviceMap',
                        'zenoss.snmp.InterfaceMap',
                        'zenoss.snmp.RouteMap',
                        'zenoss.snmp.IpServiceMap',
                        'zenoss.snmp.HRFileSystemMap',
                        'zenoss.snmp.HRSWRunMap',
                        'zenoss.snmp.CpuMap',
                        'zenoss.snmp.DellCPUMap',
                        'zenoss.snmp.DellPCIMap',
                        'zenoss.snmp.HPCPUMap',
                    ), type = 'lines')
        except KeyError: pass

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
                    ), type = 'lines')
        except Exception: pass

zCollectorPlugins()
