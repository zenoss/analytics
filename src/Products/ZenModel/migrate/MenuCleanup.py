##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class MenuCleanup(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):

        zenMenus = dmd.zenMenus

        edit = zenMenus.Edit
        removeItems(edit, ['setGroups', 'setLocation', 'setPerformanceMonitor',
                           'setPriority', 'setProductionState', 'setSystems'])

        topLevel = zenMenus.TopLevel
        removeItems(topLevel, ['clearMapCache'])

        manage = zenMenus.Manage
        removeItems(manage, ['addDevice', 'lockDevices', 'pushConfig', 'changeClass',
                             'resetCommunity', 'resetIp'])

        ipinterface = zenMenus.IpInterface
        removeItems(ipinterface, ['changeMonitoring', 'deleteIpInterfaces',
                                  'lockIpInterfaces'])

        iprouteentry = zenMenus.IpRouteEntry
        removeItems(iprouteentry, ['deleteIpRouteEntries', 'lockIpRouteEntries'])

        ipservice = zenMenus.IpService
        removeItems(ipservice, ['changeMonitoring', 'deleteIpServices',
                                  'lockIpServices'])

        filesystem = zenMenus.FileSystem
        removeItems(filesystem, ['changeMonitoring', 'deleteFileSystems',
                                  'lockFileSystems'])

        osprocess = zenMenus.OSProcess
        removeItems(osprocess, ['changeMonitoring', 'deleteOSProcesses',
                                  'lockOSProcesses'])

        winservice = zenMenus.WinService
        removeItems(winservice, ['changeMonitoring', 'deleteWinServices',
                                  'lockWinServices'])

        objTemplates = zenMenus.objTemplates
        removeItems(objTemplates, ['addLocalTemplate', 'bindTemplate',
                                  'removeZDeviceTemplates'])
        
        more = zenMenus.More.zenMenuItems
        more._getOb('zPropertyEdit').description = 'Configuration Properties'
        more._getOb('zPropertyEdit_os').description = 'Configuration Properties'
        more._getOb('collectorPlugins').description = 'Modeler Plugins'
        more._getOb('deviceCustomEdit').description = 'Custom Properties'

def removeItems(menu, items):
    for item in items:
        if hasattr(menu.zenMenuItems, item):
            menu.zenMenuItems._delObject(item)
MenuCleanup()
