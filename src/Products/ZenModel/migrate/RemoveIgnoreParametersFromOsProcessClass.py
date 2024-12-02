############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Remove ignoreParameters and ignoreParametersWhenModeling from OSProcessClass
"""
import logging
import Migrate
from Products.ZenEvents.ZenEventClasses import Debug, Error
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenModel.OSProcessClass import OSProcessClass

log = logging.getLogger("zen.migrate")


class RemoveIgnoreParametersFromOsProcessClass(Migrate.Step):

    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        log.info("Removing ignoreParameters and ignoreParametersWhenModeling from all OSProcessClass objects")
        try:
            for brain in ICatalogTool(dmd).search(OSProcessClass):
                try:
                    pc = brain.getObject()
                except Exception:
                    log.warn("Failed to get %s", brain.getPath())
                else:
                    try:
                        ignore = False
                        if getattr(pc, 'ignoreParameters', False):
                            ignore = True
                            pc.ignoreParameters = False
                        if getattr(pc, 'ignoreParametersWhenModeling', False):
                            ignore = True
                            pc.ignoreParametersWhenModeling = False
                        if ignore and not getattr(pc, 'replaceRegex', False):
                            pc.replaceRegex = '.*'
                            pc.replacement = pc.name
                    except Exception:
                        log.warn("Failed to migrate %s", brain.getPath(), exc_info=True)
        except Exception:
            log.fail('Unable to search for OSProcessClass objects')

RemoveIgnoreParametersFromOsProcessClass()
