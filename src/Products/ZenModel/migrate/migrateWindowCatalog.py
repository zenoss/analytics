##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Clean up the maintenance window catalog after moving to notification
subscriptions.

'''
import Migrate

class MigrateWindowCatalog(Migrate.Step):
    version = Migrate.Version(4, 0, 1)

    def cutover(self, dmd):
        catalog = dmd.maintenanceWindowSearch
        paths = set()
        for b in catalog():
            path = b.getPath()
            if path.startswith('/zport/dmd/ZenUsers'):
                paths.add(path)
        for path in paths:
            catalog.uncatalog_object(path)

MigrateWindowCatalog()
