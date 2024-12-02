##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenWidgets.PortletManager import manage_addPortletManager
from Products.ZenWidgets.ZenossPortlets import ZenossPortlets
from Acquisition import aq_base


class PortletManager(Migrate.Step):
    version = Migrate.Version(2, 1, 1)

    def cutover(self, dmd):
        zport = aq_base(dmd.zport)
        if not hasattr(zport, 'ZenPortletManager'):
            manage_addPortletManager(zport)
        zpmgr = zport.ZenPortletManager
        ZenossPortlets.register_default_portlets(zpmgr)

PortletManager()
