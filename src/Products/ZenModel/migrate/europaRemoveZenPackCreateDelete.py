##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This removes the install zenpack and remove zenpack from the UI. This was problematic because
removing or installing a zenpack requires a restart, which includes restarting the UI.
"""

import logging
import Migrate

log = logging.getLogger("zen.migrate")

class EuropaRemoveZenPackCreateDelete(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        menu = dmd.zenMenus._getOb('ZenPack_list', None)
        for menuId in ('installZenPack', 'removeZenPack'):
            if menu.zenMenuItems._getOb(menuId, None):
                try:
                    menu.zenMenuItems._delObject(menuId)
                except Exception as e:
                    log.error("Unable to remove menu %s" % menuId)
                    log.exception(e)
        pass

EuropaRemoveZenPackCreateDelete()
