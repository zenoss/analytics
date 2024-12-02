##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Migration for ActionRule Schedule Objects

'''

__version__ = "$Revision$"[11:-2]

import Migrate

class ARSchedule(Migrate.Step):
    "Convert a data source into a data source with a data point"
    version = Migrate.Version(0, 23, 0)

    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        for u in dmd.ZenUsers.getAllUserSettings():
            for ar in u.objectValues(spec='ActionRule'):
                ar.buildRelations()

ARSchedule()
