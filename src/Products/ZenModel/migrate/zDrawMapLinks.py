##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class zDrawMapLinks(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        if not dmd.Networks.hasProperty('zDrawMapLinks'):
            dmd.Networks._setProperty(
                "zDrawMapLinks", True, type="boolean")
              


zDrawMapLinks()
