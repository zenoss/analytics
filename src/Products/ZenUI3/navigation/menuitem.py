##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from itertools import chain

import zope.interface

from Products.Five.viewlet import viewlet
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from .interfaces import INavigationItem
from .manager import SecondaryNavigationManager


@zope.interface.implementer(INavigationItem)
class PrimaryNavigationMenuItem(viewlet.ViewletBase):

    template = ViewPageTemplateFile("nav_item.pt")

    url = ""
    target = "_self"
    active_class = "active"
    inactive_class = "inactive"
    subviews = ()

    @property
    def title(self):
        return self.__name__

    @property
    def elementid(self):
        return "{0}-nav-button".format(self.__name__).replace(" ", "-")

    def update(self):
        super(PrimaryNavigationMenuItem, self).update()
        if isinstance(self.subviews, basestring):
            self.subviews = self.subviews.split()

    @property
    def selected(self):
        requestURL = self.request.getURL().replace("/@@", "/")
        for url in chain((self.url,), self.subviews):
            if re.search(url, requestURL):
                return True
        sec = SecondaryNavigationManager(
            self.context, self.request, self.__parent__
        )
        if sec:
            for v in sec.getViewletsByParentName(self.__name__):
                if v.selected:
                    return True
        return False

    @property
    def css(self):
        if self.selected:
            return self.active_class
        else:
            return self.inactive_class

    def render(self):
        """
        Render the menu item into html.
        This needs to look at the permissions from the perspective
        of the DMD. This way the menu will not change if a user has
        View Permission in one Context but not in another.
        The default zope permissions mechanism only looks at the
        permissions from the current context.
        """
        # empty permissions list means that the permission is either not set
        # or is zope2.Public (everyone can access it)
        if not self.__ac_permissions__:
            return self.template()

        # permissions come from zope looking like
        #     (('ZenCommon', ('', 'update', 'render')),)
        # NOTE: You can only have one permission per nav item
        permission = self.__ac_permissions__[0][0]
        if self.context.dmd.has_permission(permission):
            return self.template()

        # user does not have permission to view the menu item globally
        return ""


@zope.interface.implementer(INavigationItem)
class SecondaryNavigationMenuItem(PrimaryNavigationMenuItem):

    parentItem = ""

    @property
    def selected(self):
        requestURL = self.request.getURL().replace("/@@", "/")
        for url in chain((self.url,), self.subviews):
            if re.search(url, requestURL):
                return True
        return False
