##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

'''
import Migrate
from Products.ZenModel.ZenPackManager import manage_addZenPackManager
from Products.ZenModel.ZenPackPersistence import ZENPACK_PERSISTENCE_CATALOG, \
                                            CreateZenPackPersistenceCatalog

class MakeZenPackManager(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        if not getattr(dmd, 'ZenPackManager', None):
            manage_addZenPackManager(dmd, 'ZenPackManager')
            for zp in dmd.packs():
                zp.buildRelations()
                zp.moveMeBetweenRels(dmd.packs, dmd.ZenPackManager.packs)
                
        if getattr(dmd, ZENPACK_PERSISTENCE_CATALOG, None) is None:
            CreateZenPackPersistenceCatalog(dmd)
        
        for pack in dmd.ZenPackManager.packs():
            if not pack.aqBaseHasAttr('dependencies'):
                pack.dependencies = {}

MakeZenPackManager()
