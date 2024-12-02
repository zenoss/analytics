##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zEnablePassword to DeviceClass.

'''
import Migrate

class zEnablePassword(Migrate.Step):
    version = Migrate.Version(2, 5, 2)
    
    def cutover(self, dmd):
        if not dmd.Devices.hasProperty('zEnablePassword'):
            dmd.Devices._setProperty('zEnablePassword', '', type='password')

zEnablePassword()
