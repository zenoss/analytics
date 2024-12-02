##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import md5
import os

from Globals import DevelopmentMode
from AccessControl import getSecurityManager
from AccessControl.class_init import InitializeClass

from Products.ZenMessaging.audit import audit
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import ZEN_COMMON
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.Zuul.utils import ZuulMessageFactory as _t

from . import messaging
from .Portlet import Portlet


def getuid():
    return md5.md5(os.urandom(10)).hexdigest()[:8]


class DuplicatePortletRegistration(Exception):
    pass


def manage_addPortletManager(context, id="", REQUEST=None):
    """Create a portlet manager under context."""
    if not id:
        id = "ZenPortletManager"
    zpm = PortletManager(id)
    context._setObject(id, zpm)
    zpm = context._getOb(id)
    zpm.buildRelations()


class PortletManager(ZenModelRM):
    """A registry for portlet source and metadata.

    Provides access functions and handles portlet permissions.
    """

    portal_type = meta_type = "PortletManager"

    _relations = (
        (
            "portlets",
            ToManyCont(ToOne, "Products.ZenWidgets.Portlet", "portletManager"),
        ),
    )

    def register_extjsPortlet(
        self, id, title, height=200, permission=ZEN_COMMON
    ):
        """Registers an ExtJS portlet."""
        ppath = os.path.join(
            "Products", "ZenWidgets", "ZenossPortlets", "ExtPortlet.js"
        )
        self.register_portlet(
            ppath, id=id, title=_t(title), height=height, permission=permission
        )

    def register_portlet(
        self,
        sourcepath,
        id="",
        title="",
        description="",
        preview="",
        height=200,
        permission=ZEN_COMMON,
    ):
        """
        Registers a new source file and creates an associated Portlet to store
        the metadata and provide access methods.
        """
        p = self.find(id, sourcepath)
        if p:
            old_values = (
                p.sourcepath,
                p.id,
                p.title,
                p.description,
                p.preview,
                p.height,
                p.permission,
            )
            new_values = (
                sourcepath,
                id,
                _t(title),
                description,
                preview,
                height,
                permission,
            )
            if old_values == new_values:
                # Portlet unchanged - don't re-register
                return
            self.unregister_portlet(p.id)
        p = Portlet(
            sourcepath, id, _t(title), description, preview, height, permission
        )
        self.portlets._setObject(id, p)

    def unregister_portlet(self, id):
        self.portlets._delObject(id)

    def get_portlets(self):
        """
        Looks up in the registry and returns all portlet objects to which the
        current user has access.
        """
        user = getSecurityManager().getUser()
        dmd = self.dmd.primaryAq()
        return filter(
            lambda x: user.has_permission(x.permission, dmd) and x.check(),
            self.portlets(),
        )

    def find(self, id="", sourcepath=""):
        """Look for a registered portlet with an id or source path."""
        for portlet in self.portlets():
            # Special case for ExtJs portlets which will all have the same
            # sourcepath.
            if portlet.id == id or (
                portlet.sourcepath == sourcepath
                and "ExtPortlet" not in sourcepath
            ):
                return portlet
        return None

    def update_source(self, REQUEST=None):
        """Reread the source files for all portlets."""
        for portlet in self.portlets():
            portlet._read_source()

    def get_source(self, REQUEST=None):
        """
        Return the source of the portlets permitted to this user as a
        javascript file.
        """
        srcs = [x.get_source(DevelopmentMode) for x in self.get_portlets()]
        srcs.append(
            'YAHOO.register("portletsource", YAHOO.zenoss.portlet, {})'
        )
        if REQUEST:
            REQUEST.response.headers["Content-Type"] = "text/javascript"
        return "\n".join(srcs)

    def edit_portlet_perms(self, REQUEST=None):
        """Update the portlet permissions."""
        for portlet in REQUEST.form:
            if not portlet.endswith("_permission"):
                continue
            portname = portlet.split("_")[0]
            p = self.find(id=portname)
            p.permission = REQUEST.form[portlet]
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Permissions Saved",
                "Saved At: %s" % self.getCurrentUserNowString(),
            )
            REQUEST["RESPONSE"].redirect("/zport/dmd/editPortletPerms")
        audit("UI.Portlet.Edit", data_=REQUEST.form)


InitializeClass(PortletManager)
