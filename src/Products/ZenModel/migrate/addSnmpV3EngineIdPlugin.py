##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''

Adds the SnmpV3EngineIdMap collector plugin to zCollectorPlugins

'''
import Migrate

class AddSnmpV3EngineIdPlugin(Migrate.Step):
    version = Migrate.Version(4, 2, 70)
    plugin_name = 'zenoss.snmp.SnmpV3EngineIdMap'

    def cutover(self, dmd):
        for device_class in [dmd.Devices] + dmd.Devices.getSubOrganizers():
                if device_class.hasProperty('zCollectorPlugins') and 'zenoss.snmp' in " ".join(device_class.zCollectorPlugins):
                        if AddSnmpV3EngineIdPlugin.plugin_name not in device_class.zCollectorPlugins:
                                print "Collector plugin {0} added to {1}.".format(AddSnmpV3EngineIdPlugin.plugin_name, device_class.getPrimaryId())
                                if isinstance(device_class.zCollectorPlugins, tuple):
                                        l = list(device_class.zCollectorPlugins)
                                        l.append(AddSnmpV3EngineIdPlugin.plugin_name)
                                        device_class.zCollectorPlugins = tuple(l)
                                else:
                                        device_class.zCollectorPlugins.append(AddSnmpV3EngineIdPlugin.plugin_name)
                                device_class._p_changed = True

AddSnmpV3EngineIdPlugin()
