##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Set zRouteMapMaxRoutes defaults

$Id:$
'''
import Migrate

class zRouteMapMaxRoutesProperty(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        
        # Set zRouteMapMaxRoutes defaults
        if not dmd.Devices.hasProperty("zRouteMapMaxRoutes"):
            dmd.Devices._setProperty("zRouteMapMaxRoutes", 500, type="int")

zRouteMapMaxRoutesProperty()
