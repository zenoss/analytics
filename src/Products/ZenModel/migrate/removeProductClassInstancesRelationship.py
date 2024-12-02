##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate

from Acquisition import aq_base
from zope.event import notify

from Products.ZenModel.Manufacturer import Manufacturer
from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from Products.ZenRelations.ToManyRelationship import ToManyRelationship
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.utils import safe_hasattr as hasattr

from Products.ZenModel.migrate.removeEmptyProductClassRelationships import PRODUCT_CLASS_MIGRATED_MARKER

class RemoveProductClassInstancesRelationship(Migrate.Step):

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Manufacturers, PRODUCT_CLASS_MIGRATED_MARKER):
            for manufacturer in dmd.Manufacturers.values():
                if isinstance(manufacturer, Manufacturer) and hasattr(manufacturer, "products"):
                    for product in manufacturer.products():
                        if hasattr(aq_base(product), "instances") and isinstance(product.instances, ToManyRelationship):
                            instances = product.instances()
                            product._delObject("instances", suppress_events=True)
                            for instance in instances:
                                if hasattr(aq_base(instance), "productClass") and isinstance(instance.productClass, ToOneRelationship):
                                    instance._delObject("productClass", suppress_events=True)
                                    instance.setProductClass(product, raiseIndexEvent=False)

RemoveProductClassInstancesRelationship()
