##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys

from AccessControl import getSecurityManager, Unauthorized
from Products.Five.browser import BrowserView, pagetemplatefile
from zope.component import queryMultiAdapter
from zope.viewlet.interfaces import IViewletManager


class MainPageRedirect(BrowserView):
    def __call__(self):
        self.request.response.redirect("/zport/dmd/dashboard")


class ErrorMessage(BrowserView):
    def _get_viewlets(self, provider, role="_ZenCommon_Permission"):
        """
        In the case of a NotFound, there is no authenticated user available, as
        a last resort check session if we have user logged in and if not
        raise Unauthorize.

        In the case of another exception type, we have the user, but
        security isn't entirely set up correctly, so we have to make this view
        appear to be in the context (it actually has none, not being an
        Acquisition.Implicit).

        The upshot of all this is that for exceptions, nav will appear only
        for authenticated user.
        """
        # Check to see if we're authenticated
        userid = getSecurityManager().getUser().getId()
        if userid is None:
            # Not authenticated, check session if we have user logged in
            if not self.request.SESSION.get("__ac_logged_as"):
                raise Unauthorized
            self.__ac_local_roles__ = {userid: [role]}
        else:
            # Authenticated, force this view to be in a working context
            self._parent = self.dmd
        # Look up the viewlets
        mgr = queryMultiAdapter(
            (self.dmd, self.request, self), IViewletManager, provider
        )
        # Activate the viewlets
        mgr.update()
        if userid is None:
            # No security stuff is in place, because we're not authenticated,
            # so the manual permission checking in
            # ZenUI3.navigation.menuitem.PrimaryNavigationMenuItem.render will
            # cause nothing to be returned. Short-circuit permissions, since
            # dmd doesn't have them set anyway. Since we're already using the
            # most restrictive authenticated role there is, this won't cause
            # anything to display that shouldn't.
            for viewlet in mgr.viewlets:
                viewlet.__ac_permissions__ = None
        return mgr.render()

    @property
    def headExtra(self):
        return self._get_viewlets("head-extra")

    @property
    def primaryNav(self):
        return self._get_viewlets("primarynav")

    @property
    def secondaryNav(self):
        return self._get_viewlets("secondarynav")

    @property
    def dmd(self):
        return self.request.other["PARENTS"][-1].zport.dmd

    @property
    def instanceIdentifier(self):
        return self.dmd.instanceIdentifier

    @property
    def zenossVersion(self):
        return self.dmd.About.getZenossVersionShort()

    @property
    def isNotFound(self):
        return self.context.__class__.__name__ == "NotFound"

    @property
    def error_message(self):
        t, v, tb = sys.exc_info()
        return self.dmd.zenoss_error_message(
            error_type=t, error_value=v, error_traceback=tb, error_message=v
        )

    def __call__(self):
        t = pagetemplatefile.ViewPageTemplateFile("error_message.pt")
        return t(self)
