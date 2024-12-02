##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Operations for Navigation

Available at:  /zport/dmd/detailnav_router
"""

import logging
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenUI3.security.security import permissionsForContext
from Products.ZenUtils.Utils import zenPath
# page stats logger
log = logging.getLogger('zen.pagestats')
# create file handler which logs even debug messages
fh = logging.FileHandler(zenPath('log' + '/pagestats.log'))
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)

# error log logger
errorlog = logging.getLogger('javascripterrors')
fh = logging.FileHandler(zenPath('log' + '/javascript_errors.log'))
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(message)s')
fh.setFormatter(formatter)
errorlog.addHandler(fh)


class DetailNavRouter(DirectRouter):
    """
    Router to Details navigation for given uid
    """

    def _getLinkMenuItems(self, menuIds, ob):
        def filterFn(menu):
            return not menu.isdialog
        items = filter(filterFn, self._getMenuItems(menuIds, ob))
        return items

    def _getDialogMenuItems(self, menuIds, ob):
        def filterFn(menu):
            return menu.isdialog
        items = filter(filterFn, self._getMenuItems(menuIds, ob))
        return items

    def _getMenuItems(self, menuIds, ob):
        linkMenus = []
        menus = ob.getMenus(menuIds)
        if menus:
            if isinstance(menus, list):
                menus = [menus];
            else:
                menus = menus.values()
            for menuItems in menus:
                for menuItem in menuItems:
                    linkMenus.append(menuItem)
        return linkMenus

    def getDetailNavConfigs(self, uid=None, menuIds=None):
        """
        return a list of Detail navigation configurations. Can be used to create
        navigation links. Format is:
        {
        id: <id of the configuration>,
        'viewName': <view to display>,
        'xtype': <Ext type for the panel>,
        'text': <display name of the config info>
        }
        """
        detailItems = []
        def convertToDetailNav(tab):
            return {
                    'id': '%s' % tab['name'].lower(),
                    'xtype': 'backcompat',
                    'viewName': tab['action'],
                    'text': tab['name']
                    }
        def menuToNav(menu):
            return {
                    'id': '%s' % menu.id.lower(),
                    'xtype': 'backcompat',
                    'viewName': menu.action,
                    'text': menu.description
                    }

        if uid:
            ob = self.context.dmd.unrestrictedTraverse(uid)
            tabs = ob.zentinelTabs('')
            detailItems = [ convertToDetailNav(tab) for tab in tabs ]
            #get menu items that are not dialogs
            if menuIds:
                menus = self._getLinkMenuItems(menuIds, ob)
                if menus:
                    detailItems.extend(menuToNav(menu) for menu in menus)
        return DirectResponse(detailConfigs=detailItems)

    def getContextMenus(self, uid=None, menuIds=None):
        if uid:
            ob = self.context.dmd.unrestrictedTraverse(uid)
            menuItems = []
            if menuIds:
                menus = self._getDialogMenuItems(menuIds, ob)
                def menuToConfig(menu):
                    return {
                            'id': '%s' % menu.id.lower(),
                            'viewName': menu.action,
                            'text': menu.description
                            }
                if menus:
                    menuItems.extend(menuToConfig(menu) for menu in menus)
        return DirectResponse(menuItems=menuItems)

    def getSecurityPermissions(self, uid):
        """
        returns a dictionary of all the permissions a
        user has on the context
        """
        obj = self.context.dmd.unrestrictedTraverse(uid)
        permissions = permissionsForContext(obj)
        return DirectResponse.succeed(data=permissions)

    def recordPageLoadTime(self, page, time):
        user = self.context.zport.dmd.ZenUsers.getUserSettings()
        log.info("PAGELOADTIME: %s %s %s (seconds)", user.id, page, time)

    def logErrorMessage(self, msg="", url="", file="", lineNumber=""):
        """
        Records an error message from the client. 
        """
        user = self.context.zport.dmd.ZenUsers.getUserSettings()
        errorlog.error("User: %s - %s '%s' at %s line:%s", user.id, url, msg, file, lineNumber)
