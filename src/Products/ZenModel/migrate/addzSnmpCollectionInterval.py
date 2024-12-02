##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zSnmpCollectionInterval z property.  This replaces the per-collector
configuration property and allows for per-device collection intervals.

'''
import Migrate


class addzSnmpCollectionInterval(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        if not hasattr( dmd.Devices, 'zSnmpCollectionInterval' ):
            localMonitor = dmd.Monitors.getPerformanceMonitor('localhost')
            collectorDefault = localMonitor.perfsnmpCycleInterval
            dmd.Devices._setProperty('zSnmpCollectionInterval',
                                     collectorDefault,
                                     'int')


addzSnmpCollectionInterval()
