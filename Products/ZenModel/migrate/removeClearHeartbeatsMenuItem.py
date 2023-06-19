##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Remove the 'Clear Heartbeats' menu item used on the Device page
as it is considered confusing. See ZEN-1101.
"""
import os
import logging
from Products.ZenModel.migrate import Migrate
from Products.Zuul import getFacade


log = logging.getLogger('zen.migrate')

class removeClearHeartbeatsMenuItem(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        try:
            dmd.zenMenus.Manage.zenMenuItems._remove(dmd.zenMenus.Manage.zenMenuItems.clearHeartbeats)
        except AttributeError:
            pass # it didn't exist anyway

removeClearHeartbeatsMenuItem()
