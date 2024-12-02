##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.publisher.interfaces.browser import (
    IBrowserSkinType,
    IDefaultBrowserLayer,
)
from zope.viewlet.interfaces import IViewletManager, IViewlet


class IPrimaryNavigationMenu(IViewletManager):
    """
    Navigation menu viewlet manager.
    """


class ISecondaryNavigationMenu(IViewletManager):
    """
    Navigation menu viewlet manager.
    """


class INavigationItem(IViewlet):
    """
    A navigable item.
    """


class IZenossNav(IBrowserSkinType, IDefaultBrowserLayer):
    """
    Marker interface for our nav layer
    """
