##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.Jobber.manager import manage_addJobManager

class addJobManager(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        if not hasattr(dmd, 'JobManager'):
            manage_addJobManager(dmd)


addJobManager()
