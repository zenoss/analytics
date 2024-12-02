##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class HappierZenPackRels(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for p in dmd.ZenPackManager.packs():
            p.buildRelations() # This is probably not necessary
            p.manager.obj = dmd.ZenPackManager
            p._p_changed = True


HappierZenPackRels()
