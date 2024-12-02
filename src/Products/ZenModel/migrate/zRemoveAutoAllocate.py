##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class zRemoveAutoAllocate(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if dmd.Networks.hasProperty('zAutoAllocateScript'):
            dmd.Networks._delProperty("zAutoAllocateScript")

zRemoveAutoAllocate()
