##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""
File systems windows file systems use their mount as the name of the component but they
are indexed under titleOrId (which is their id).
"""

import Migrate
import logging
from zope.event import notify
from Products.ZenModel.FileSystem import FileSystem
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.catalog.events import IndexingEvent
log = logging.getLogger('zen.migrate')

class FileSystemIndexName(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        for brain in ICatalogTool(dmd).search(FileSystem):
            try:
                filesystem = brain.getObject()
                notify(IndexingEvent(filesystem, idxs=('name',)))
            except Exception:
                try:
                    log.warn("Unable to reindex %s", brain.getPath())
                except Exception:
                    log.warn("Unable to reindex unbrainable item")

FileSystemIndexName()
