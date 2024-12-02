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
from Products.Zuul.catalog.model_catalog_init import reindex_model_catalog
from Products.Zuul.catalog.indexable import DeviceIndexable
from Products.Zuul.catalog.interfaces import IModelCatalogTool


log = logging.getLogger("zen.migrate")

class AddIndexesForDevice(Migrate.Step):
    """
    Adds new indexes for devices in scope of adding new router which gives a possibility
    to pull data directly from SOLR without touching ZODB.
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):

        search_results = IModelCatalogTool(dmd).devices.search(limit=1, fields=["pythonClass"])
        if search_results.total > 0 and search_results.results.next().pythonClass is None:

            log.info("Performing of adding new indexes for devices, this can take a while.")

            reindex_model_catalog(dmd,
                root="/zport/dmd/Devices",
                idxs=("tagNumber",
                    "pythonClass",
                    "priority",
                    "collector",
                    "osModel",
                    "osManufacturer",
                    "hwModel",
                    "hwManufacturer",
                    "serialNumber"),
                types=DeviceIndexable)


AddIndexesForDevice()
