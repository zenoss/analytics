##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenModel.RRDTemplate import YieldAllRRDTemplates
from Products.ZenModel.ZenPackPersistence import ZenPackPersistence

class ReindexZenPackPerstence(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for t in YieldAllRRDTemplates(dmd):
            for ds in t.datasources():
                if isinstance(ds, ZenPackPersistence):
                    ds.index_object()

ReindexZenPackPerstence()
