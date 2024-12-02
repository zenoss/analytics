##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zLinks to DeviceClass.

'''
import Migrate

class zLinks(Migrate.Step):
    version = Migrate.Version(1, 0, 0)
    
    def cutover(self, dmd):
        if not dmd.Devices.hasProperty('zLinks'):
            dmd.Devices._setProperty('zLinks', '', 'text', 'Links', True)

zLinks()
