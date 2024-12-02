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


class addzSnmpContext(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        if not hasattr( dmd.Devices, 'zSnmpContext' ):
            dmd.Devices._setProperty('zSnmpContext', '', type="string")


addzSnmpContext()
