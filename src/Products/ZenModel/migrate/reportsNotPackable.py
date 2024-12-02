##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class ReportsNotPackable(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    

    def cutover(self, dmd):
        if dmd.zenMenus.Report_list.zenMenuItems._getOb('addToZenPack', False):
            dmd.zenMenus.Report_list.zenMenuItems._delObject('addToZenPack')


ReportsNotPackable()
