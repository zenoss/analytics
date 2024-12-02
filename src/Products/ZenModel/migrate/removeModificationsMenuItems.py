##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Remove Modifications menu items.

$Id:$
'''
import Migrate
from Products.Zuul.interfaces import ICatalogTool

class RemoveModificationsMenuItems(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        items = ICatalogTool(dmd).search('Products.ZenModel.ZenMenuItem.ZenMenuItem')
        for brain in items:
            menuitem = brain.getObject()
            action = menuitem.action
            if action in ('../viewHistory', 'viewHistory', 'viewNewHistory'):
                menuitem.__primary_parent__.removeRelation(menuitem)

RemoveModificationsMenuItems()
