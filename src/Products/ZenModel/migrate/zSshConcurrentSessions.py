##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zSshConcurrentSessions to /Devices.

'''
import Migrate

class zSshConcurrentSessions(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        # Install the zSshConcurrentSessions zProperty
        if not dmd.Devices.hasProperty('zSshConcurrentSessions'):
            dmd.Devices._setProperty('zSshConcurrentSessions', 10, type="int")

zSshConcurrentSessions()
