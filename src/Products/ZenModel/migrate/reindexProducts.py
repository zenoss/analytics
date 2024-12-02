##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class ReindexProducts(Migrate.Step):

    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        dmd.Manufacturers.productSearch.reIndex()


ReindexProducts()
