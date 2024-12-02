##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''

Add zCollectorDecoding to DeviceClass.

$Id:$
'''
import Migrate

class ZCollectorDecoding(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zCollectorDecoding"):
            dmd.Devices._setProperty("zCollectorDecoding", 'utf-8')
        elif dmd.Devices.hasProperty("zCollectorDecoding"):
            dmd.Devices._delProperty("zCollectorDecoding")
            dmd.Devices._setProperty("zCollectorDecoding", 'utf-8')

ZCollectorDecoding()
