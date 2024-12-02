##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class zZenDiscLove(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        if not dmd.Networks.hasProperty('zAutoAllocateScript'):
            dmd.Networks._setProperty(
                "zAutoAllocateScript", ["#your python script here", "#avail objs: dmd, dev, log"], type="lines")
              
        if not dmd.Networks.hasProperty('zZenDiscCommand'):
            dmd.Networks._setProperty(
                "zZenDiscCommand", "zendisc run --net=${here/id}", type="string")


zZenDiscLove()
