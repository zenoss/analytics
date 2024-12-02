##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl import ClassSecurityInfo, Permissions
from ZenMenu import ZenMenu
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base, aq_chain
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import cmpClassNames
from Products.ZenWidgets import messaging

class ZenMenuable:
    """ ZenMenuable is a mixin providing menuing.
    """

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenu')
    def manage_addZenMenu(self, id=None, desc='', REQUEST=None):
        """ Add a menu item to this device organizer """
        mu = None
        if id:
            mu = ZenMenu(id)
            self.zenMenus._setObject(id, mu)
            mu = self.zenMenus._getOb(id)
            if self.meta_type == 'Device':
                self.setLastChange()
            mu.description = desc
        if REQUEST:
            if mu:
                messaging.IMessageSender(self).sendToBrowser(
                    'Menu Added',
                    'The menu "%s" has been added.' % mu.id
                )
                url = '%s/zenMenus/%s' % (self.getPrimaryUrlPath(), mu.id)
                return REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return mu


    security.declareProtected('Change Device', 'manage_addZenMenuItem')
    def manage_addZenMenuItem(self, menuid, id=None, description='', action='', 
            permissions=(Permissions.view,), isdialog=False, isglobal=True, 
            banned_classes=(), allowed_classes=(), banned_ids=(), ordering=0.0, 
            REQUEST=None):
        """ Add ZenMenuItem
        """
        menu = getattr(self.zenMenus, menuid, None) 
        if not menu: menu = self.manage_addZenMenu(menuid)
        menu.manage_addZenMenuItem(id, description, action, 
                permissions, isdialog, isglobal, 
                banned_classes, allowed_classes, banned_ids, ordering)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'manage_deleteZenMenuItem')
    def manage_deleteZenMenuItem(self, menuid, delids=(), REQUEST=None):
        """ Delete Menu Items """
        menu = getattr(self.zenMenus, menuid, None) 
        if menu:
            menu.manage_deleteZenMenuItem(delids)
        if REQUEST:
            return self.callZenScreen(REQUEST)

                
    security.declareProtected('Change Device', 'manage_saveMenuItemOrdering')
    def manage_saveMenuItemOrdering(self, menuid, REQUEST=None):
        """ Delete Menu Items """
        menu = getattr(self.zenMenus, menuid, None)
        if menu and REQUEST:
            for menuitem in getattr(self.zenMenus, menuid).zenMenuItems():
                ordering = REQUEST[menuitem.id]
                menuitem.ordering = ordering
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'manage_addItemsToZenMenu')
    def manage_addItemsToZenMenu(self, menuid, items=None):
        """ Add ZenMenuItems to a ZenMenu. 
            Accepts a list of dictionaries.
            Available keyword args:
              id
              description
              action
              permissions
              isglobal
              isdialog
              banned_classes
              allowed_classes
              banned_ids
        """
        if not items:
            items = [{}]
        menu = getattr(self.zenMenus, menuid, None)
        if not menu: menu = self.manage_addZenMenu(menuid)
        if isinstance(items, dict): items = [items]
        for item in items:
            menu.manage_addZenMenuItem(**item)
        return menu

    security.declareProtected('Change Device', 'buildMenus')
    def buildMenus(self, menudict={}):
        """ Build menus from a dictionary. """
        for k,v in menudict.iteritems():
            self.manage_addItemsToZenMenu(k, v)

    security.declareProtected('Change Device', 'manage_deleteZenMenu')
    def manage_deleteZenMenu(self, delids=(), REQUEST=None):
        """ Delete Menu Items from this object """
        if isinstance(delids,(str,unicode)): delids = [delids]
        for id in delids:
            self.zenMenus._delObject(id)
        if self.meta_type == 'Device':
            self.setLastChange()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Menus Deleted',
                'The menus %s have been deleted.' % (', '.join(delids))
            )
            return self.callZenScreen(REQUEST)

    #security.declareProtected('View', 'getMenus')
    def getMenus(self, menuids=None, context=None):
        """ Build menus for this context, acquiring ZenMenus
            which in turn acquire ZenMenuItems.

            Pass it a menuid for a list of menuitems, 
            a sequence of menuids for a dict of lists of items, 
            or nothing for a dict of all available menus.
        """ 
        if not context: context=self
        menus = {}
        if not isinstance(self, ZenMenuable): return None
        if isinstance(menuids, (str,unicode)): menuids=[menuids]
        mychain = aq_chain(context.primaryAq())
        mychain.reverse()
        for obj in mychain:
            if getattr(aq_base(obj), 'zenMenus', None):
                mens = obj.zenMenus()
                while mens:
                    c = mens.pop()
                    if menuids and c.id not in menuids: continue
                    menu = menus[c.id] = menus.get(c.id, {})
                    its = c.zenMenuItems()
                    while its:
                        i = its.pop()
                        def permfilter(p): 
                            return self.checkRemotePerm(p,context)
                        permok = filter(permfilter,
                            getattr(i,'permissions',('',)))
                        if not permok \
                           or (not getattr(i, 'isglobal', True) and \
                               context!=i.getMenuItemOwner())\
                           or (context.id in i.banned_ids) \
                           or (i.allowed_classes and not \
                              cmpClassNames(context, i.allowed_classes))\
                           or cmpClassNames(context, i.banned_classes):
                            continue
                        menu[i.id] = i
        keys = menus.keys()
        for key in keys:
            menus[key] = menus[key].values()
            if not menus[key]: del menus[key]
        if not menus: 
            return None
        elif len(menus.keys())==1: 
            return menus.values()[0]
        else:
            return menus

InitializeClass(ZenMenuable)
