##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
import logging

from Acquisition import aq_base

from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.utils import safe_hasattr as hasattr

log = logging.getLogger("zen.migrate")

PRODUCT_CLASS_MIGRATED_MARKER = "product_class_relationship_removed"

class RemoveEmptyProductClassRelationships(Migrate.Step):
    """
    This migrate script completes the work of RemoveProductClassInstancesRelationship to delete
    the productClass relationship from products that have a empty productClass relationship.
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        # This needs to get run a second time after re-indexing has occurred
        run_count = getattr(dmd.Manufacturers, PRODUCT_CLASS_MIGRATED_MARKER, 0)
        if run_count < 2:
            for brain in IModelCatalogTool(dmd).search("Products.ZenModel.MEProduct.MEProduct"):
                try:
                    product = brain.getObject()
                except KeyError:
                    log.warn("Found stale object in catalog: {}".format(brain.getPath()))
                else:
                    if hasattr(aq_base(product), "productClass") and isinstance(product.productClass, ToOneRelationship):
                        if not product.productClass():
                            product._delObject("productClass", suppress_events=True)
            setattr(dmd.Manufacturers, PRODUCT_CLASS_MIGRATED_MARKER, run_count + 1)

RemoveEmptyProductClassRelationships()
