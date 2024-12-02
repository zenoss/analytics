##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """AddUserInterfaceSettings

Adds a zodb object that is a collection of user configurable settings
that affect the behavior of the User Interface.
"""

import Migrate
from Products.ZenModel.UserInterfaceSettings import UserInterfaceSettings
from Products.Zuul.utils import safe_hasattr as hasattr

class AddUserInterfaceSettings(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if not hasattr(dmd, 'UserInterfaceSettings'):
            settings = UserInterfaceSettings('UserInterfaceSettings')

            # copy settings that were previously on the data root
            settings.enableLiveSearch = getattr(dmd, 'enableLiveSearch', True)
            settings.incrementalTreeLoad = getattr(dmd, 'incrementalTreeLoad', False)

            dmd._setObject('UserInterfaceSettings', settings)

AddUserInterfaceSettings()
