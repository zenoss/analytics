##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Reexecute zenprocs.sql to get new version of procedures (now parameterized)

'''
import Migrate
from Products.ZenUtils.path import zenPath

import os

class ProcParams(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        procs = zenPath('Products', 'ZenEvents', 'db', 'zenprocs.sql')
        os.system('cat %s | mysql -u%s -p%s %s' % (
                    procs,
                    dmd.ZenEventManager.username,
                    dmd.ZenEventManager.password,
                    dmd.ZenEventManager.database))
        

ProcParams()
