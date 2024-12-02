##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zCollectorLogChanges defaults

$Id:$
'''
import Migrate

class zCollectorLogChanges(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        
        # Set zCollectorLogChanges defaults
        if not dmd.Devices.hasProperty("zCollectorLogChanges"):
            dmd.Devices._setProperty("zCollectorLogChanges", 
                                                                                True, type="boolean")
        else:
            dmd.Devices.zCollectorLogChanges = True
        
zCollectorLogChanges()
