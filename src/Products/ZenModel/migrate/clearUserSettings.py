##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.facades import ObjectNotFoundException

__doc__ = """
The user preference settings for trees and grids conflict between ExtJS3 and 4, this migrate
script removes them all.
"""

import Migrate
import logging
from Products.Zuul.interfaces import ICatalogTool
log = logging.getLogger('zen.migrate')




class ClearUserSettings(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if not hasattr(dmd, '_clearedUserSettingsExtJs4'):
            for brain in ICatalogTool(dmd).search('Products.ZenModel.UserSettings.UserSettings'):
                user = brain.getObject()
                if hasattr(user, '_browser_state'):
                    del brain.getObject()._browser_state
            dmd._clearedUserSettingsExtJs4 = True

ClearUserSettings()
