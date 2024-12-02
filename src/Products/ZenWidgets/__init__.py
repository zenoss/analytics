##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.CMFCore.DirectoryView import registerDirectory
from Products.Five.browser import BrowserView

from .ZenossPortlets.ZenossPortlets import register_default_portlets
from .ZenTableManager import manage_addZenTableManager, ZenTableManager

registerDirectory("skins", globals())


def update_portlets(app):
    """Reread in portlet source on startup.

    If this is the initial load, and objects don't exist yet, don't do
    anything.
    """
    if hasattr(app, "zport") and hasattr(app.zport, "ZenPortletManager"):
        register_default_portlets(app.zport.ZenPortletManager)
        for pack in app.zport.dmd.ZenPackManager.packs():
            for portlet in getattr(pack, "register_portlets", lambda *x: ())():
                if app.zport.ZenPortletManager.find(portlet["id"]) is None:
                    app.zport.ZenPortletManager.register_extjsPortlet(
                        **portlet
                    )


def initialize(registrar):
    registrar.registerClass(
        ZenTableManager,
        permission="Add ZenTableManager",
        constructors=(manage_addZenTableManager,),
        icon="ZenTableManager_icon.gif",
    )


def registerPortlets(event):
    """Handler for IZopeApplicationOpenedEvent which registers portlets."""
    update_portlets(event.app)


class ExtJSShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse("++resource++extjs")[name]
