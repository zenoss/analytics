##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zXmlRpcMonitorIgnore to DeviceClass and XmlRpc to EventClass.

'''
import Migrate

class PerfXmlRpc(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zXmlRpcMonitorIgnore"):
            dmd.Devices._setProperty("zXmlRpcMonitorIgnore", 
                                     False, type="boolean")

        dmd.Events.createOrganizer("/Status/XmlRpc")
        dmd.Events.createOrganizer("/Perf/Snmp")
        dmd.Events.createOrganizer("/Perf/CPU")
        dmd.Events.createOrganizer("/Perf/Interface")
        dmd.Events.createOrganizer("/Perf/Memory")
        dmd.Events.createOrganizer("/Perf/Filesystem")

PerfXmlRpc()
