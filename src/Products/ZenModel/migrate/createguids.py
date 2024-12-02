##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import Migrate

from Products.ZCatalog.Catalog import CatalogError
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier

log = logging.getLogger("zen.migrate")

class CreateMissingGuids(Migrate.Step):
    version = Migrate.Version(4, 0, 0)
    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        force = getattr(dmd, 'guid_table', None) is None

        log.debug('Creating GUIDs...')
        identifiables = [o.__name__ for o in IGloballyIdentifiable.dependents.keys()]
        catalog = dmd.global_catalog
        update_metadata = False
        try:
            catalog._catalog.addColumn('uuid')
            update_metadata = True
        except CatalogError:
            # Column exists
            pass
        for brain in ICatalogTool(dmd).search(identifiables):
            try:
                obj = brain.getObject()
            except Exception:
                continue
            identifier = IGlobalIdentifier(obj)
            if force or not identifier.getGUID():
                guid = identifier.create(force)
                log.debug('Created guid for %s: %s', '/'.join(obj.getPrimaryPath()[3:]), guid)
            if update_metadata:
                catalog.catalog_object(obj, idxs=(), update_metadata=True)


CreateMissingGuids()
