##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import zope.component
import zope.interface

from Products.Five.viewlet.manager import ViewletManagerBase

from interfaces import IPrimaryNavigationMenu, ISecondaryNavigationMenu


def viewletSortKey(args):
    """
    Creates a sort key for this viewlet. Primary sort is viewlet weight, and
    secondary is viewlet name, guaranteeing the same order on each call.
    """
    name, viewlet = args
    try:
        return (float(viewlet.weight), name)
    except (AttributeError, ValueError):
        return 0


class WeightOrderedViewletManager(ViewletManagerBase):
    """Weight ordered viewlet managers."""

    def sort(self, viewlets):
        return sorted(viewlets, key=viewletSortKey)


class PrimaryNavigationManager(WeightOrderedViewletManager):
    zope.interface.implements(IPrimaryNavigationMenu)


@zope.interface.implementer(ISecondaryNavigationMenu)
class SecondaryNavigationManager(WeightOrderedViewletManager):
    """
    A secondary level of navigation.

    Knows how to look up the parent item to see if it is selected.
    """

    def getViewletsByParentName(self, name):
        if not hasattr(self, "viewlets"):
            self.update()
        return [v for v in self.viewlets if v.parentItem == name]

    def getActivePrimaryName(self):
        primary = PrimaryNavigationManager(
            self.context, self.request, self.__parent__
        )
        primary.update()
        for v in primary.viewlets:
            if v.selected:
                return v.__name__
        return None

    def getActiveViewlets(self):
        viewlets = []
        primaryName = self.getActivePrimaryName()
        if primaryName:
            viewlets = self.getViewletsByParentName(primaryName)
        return viewlets

    def render(self):
        return "\n".join(v.render() for v in self.getActiveViewlets())
