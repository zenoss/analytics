##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zKeyPath to DeviceClass.

$Id:$
'''
import Migrate

class KeyPath(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zKeyPath"):
            dmd.Devices._setProperty("zKeyPath", "~/.ssh/id_dsa")

KeyPath()
