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
from Products.ZenModel.RRDTemplate import CreateRRDTemplatesCatalog, \
                                            RRDTEMPLATE_CATALOG

class MakeTemplateCatalog(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    # This creates the catalog if it doesn't exist.  Indexing of the templates
    # happens in the twotwoindexing.py step.

    def cutover(self, dmd):                
        if getattr(dmd, RRDTEMPLATE_CATALOG, None) is None:
            CreateRRDTemplatesCatalog(dmd)

makeTemplateCatalog = MakeTemplateCatalog()
