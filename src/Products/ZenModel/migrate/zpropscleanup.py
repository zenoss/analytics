##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zWmiMonitorIgnore to DeviceClass.

$Id:$
'''
import Migrate

class zPropsCleanup(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        if dmd.Devices.zProdStateThreshold == 500:
            dmd.Devices.zProdStateThreshold = 300
        if dmd.Devices.hasProperty('zCollectorCollectPlugins'):
            dmd.Devices._delProperty('zCollectorCollectPlugins')
        if dmd.Devices.hasProperty('zCollectorIgnorePlugins'):
            dmd.Devices._delProperty('zCollectorIgnorePlugins')
        if dmd.Devices.hasProperty('zTransportPreference'):
            dmd.Devices._delProperty('zTransportPreference')

zPropsCleanup()
