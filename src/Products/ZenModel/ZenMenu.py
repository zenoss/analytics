##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from ZenMenuItem import ZenMenuItem
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo, Permissions
import logging
log = logging.getLogger("zen.Menu")

from ZenPackable import ZenPackable


class ZenMenu(ZenModelRM, ZenPackable):
    """ A Menu object that holds Menu Items. 
    """
    
    meta_type = 'ZenMenu'
    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    _relations =  ZenPackable._relations + (
        ("zenMenuItems", ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenuItem', 'zenMenus')),
        ("menuable", ToOne(
            ToManyCont, 'Products.ZenModel.ZenMenuable', 'zenMenus')),
        ) 

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenuItem')
    def manage_addZenMenuItem(self, id=None, description='', action='', 
            permissions=(Permissions.view,), isdialog=False, isglobal=True, 
            banned_classes=(), allowed_classes=(), banned_ids=(), ordering=0.0, 
                              REQUEST=None):
        """ Add a menu item to a menu """
        mi = None
        if id:
            mi = ZenMenuItem(id)
            self.zenMenuItems._setObject(id, mi)
            mi = self.zenMenuItems._getOb(mi.id)
            mi.description = description
            mi.action = action
            mi.permissions = permissions
            mi.isdialog = isdialog
            mi.isglobal = isglobal
            mi.banned_classes = list(banned_classes)
            mi.allowed_classes = list(allowed_classes)
            mi.banned_ids = list(banned_ids)
            mi.ordering = ordering
        return mi
 
    security.declareProtected('Change Device', 'manage_deleteZenMenuItem')
    def manage_deleteZenMenuItem(self, delids=(), REQUEST=None):
        """ Delete Menu Items """
        if isinstance(delids, (str,unicode)): delids = [delids]
        for id in delids:
            self.zenMenuItems._delObject(id)
        

InitializeClass(ZenMenu)
