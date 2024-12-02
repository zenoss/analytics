##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Set zWmiMonitorIgnore defaults
Remove zWmiMonitorIgoner

$Id:$
'''
import Migrate

class zWmiMonitorProperty(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        
        # Set zWmiMonitorIgnore defaults
        if not dmd.Devices.hasProperty("zWmiMonitorIgnore"):
            dmd.Devices._setProperty("zWmiMonitorIgnore", True, type="boolean")
        else:
            dmd.Devices._updateProperty('zWmiMonitorIgnore', True)

        try:
            win = dmd.Devices.getOrganizer("/Server/Windows")
            if not win.hasProperty("zWmiMonitorIgnore"):
                win._setProperty("zWmiMonitorIgnore", False, type="boolean")
            else:
                win._updateProperty('zWmiMonitorIgnore', False)
        except KeyError: pass
        
        # Delete misspelled zProp
        for dc in dmd.Devices.getSubOrganizers():
            if dc.hasProperty('zWmiMonitorIgoner'):
                dc._delProperty('zWmiMonitorIgoner')

        for dev in dmd.Devices.getSubDevicesGen():
            if dev.hasProperty('zWmiMonitorIgoner'):
                dev._delProperty('zWmiMonitorIgoner')


zWmiMonitorProperty()
