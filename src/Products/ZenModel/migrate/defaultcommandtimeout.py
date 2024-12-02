##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Change zCommandCommandTimeout at /Devices to 15 if it is currently less
than 15.

'''
import Migrate

class DefaultCommandTimeout(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if dmd.Devices.zCommandCommandTimeout < 15.0:
            dmd.Devices.zCommandCommandTimeout = 15.0

DefaultCommandTimeout()
