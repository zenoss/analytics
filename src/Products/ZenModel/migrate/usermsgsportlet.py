##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenWidgets.ZenossPortlets.ZenossPortlets import \
                                                    register_default_portlets

class UserMsgsPortlet(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        for us in dmd.ZenUsers.getAllUserSettings():
            us.buildRelations()
        zpm = dmd.zport.ZenPortletManager
        register_default_portlets(zpm)

UserMsgsPortlet()
