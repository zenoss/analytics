##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = '''
This migration script added a device index fir snmpLastCollection attribute
'''

import Migrate
import logging

from Products.Zuul.catalog.model_catalog_init import reindex_model_catalog
from Products.Zuul.catalog.indexable import DeviceIndexable
from Products.Zuul.catalog.interfaces import IModelCatalogTool

log = logging.getLogger("zen.migrate")


class AddSnmpLastCollectionIndex(Migrate.Step):

    version = Migrate.Version(200, 6, 0)

    def cutover(self, dmd):

        search_results = IModelCatalogTool(dmd).devices.search(
            limit=1, fields=["snmpLastCollection"]
        )
        if search_results.total > 0 and \
                search_results.results.next().snmpLastCollection is None:
            log.info("Adding index for last model time, this can take a "
                     "while.")
            reindex_model_catalog(dmd,
                root="/zport/dmd/Devices",
                idxs=("snmpLastCollection"),
                types=DeviceIndexable)
        else:
            log.info("Index for last model time already exists, skipping.")


AddSnmpLastCollectionIndex()

