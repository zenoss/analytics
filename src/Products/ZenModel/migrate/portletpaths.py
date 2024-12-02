##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenWidgets.ZenossPortlets.ZenossPortlets import portlets

class PortletPaths(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        zpm = dmd.zport.ZenPortletManager
        for portlet in portlets:
            pobj = zpm.find(portlet['id'])
            if pobj: pobj.sourcepath = portlet['sourcepath']

PortletPaths()
