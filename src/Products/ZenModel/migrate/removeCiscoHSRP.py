##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
    The zenoss.snmp.CiscoHSRP modeler plugin was broken several versions ago
    when the zenmodeler daemon was converted to a PBDaemon. This migrate script
    removes references to the modeler plugin from the system.
    """

import logging
log = logging.getLogger('zen.migrate')

import Migrate

def removeModelerPlugin(obj, plugin_name):
    if not obj.hasProperty('zCollectorPlugins'):
        return

    plugins = obj.zCollectorPlugins
    if 'zenoss.snmp.CiscoHSRP' in plugins:
        log.info("Removing zenoss.snmp.CiscoHSRP modeler plugin from %s",
            obj.titleOrId())
        pluginsList = list(plugins)
        pluginsList.remove('zenoss.snmp.CiscoHSRP')
        obj.zCollectorPlugins = tuple(pluginsList)


class RemoveCiscoHSRP(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import reindexdevices
        self.dependencies = [reindexdevices.upgradeindices]

    def cutover(self, dmd):
        plugin_name = 'zenoss.snmp.CiscoHSRP'

        # Remove the plugin from all device classes.
        removeModelerPlugin(dmd.Devices, plugin_name)

        for device_class in dmd.Devices.getSubOrganizers():
            removeModelerPlugin(device_class, plugin_name)

        # Remove the plugin from all devices.
        for device in dmd.Devices.getSubDevices():
            removeModelerPlugin(device, plugin_name)


RemoveCiscoHSRP()
