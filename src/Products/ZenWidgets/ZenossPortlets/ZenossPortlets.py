##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from Products.ZenModel.ZenossSecurity import (
    ZEN_COMMON,
    ZEN_MANAGE_DMD,
    ZEN_VIEW,
)


def _portletpath(*args):
    """
    Shortcut, since these all live in the same directory. Portlet needs a path
    relative to $ZENHOME.
    """
    return os.path.join("Products", "ZenWidgets", "ZenossPortlets", *args)


portlets = [
    {
        "sourcepath": _portletpath("HeartbeatsPortlet.js"),
        "id": "HeartbeatsPortlet",
        "title": "Daemon Processes Down",
        "permission": ZEN_MANAGE_DMD,
    },
    {
        "sourcepath": _portletpath("GoogleMapsPortlet.js"),
        "id": "GoogleMapsPortlet",
        "title": "Google Maps",
        "permission": ZEN_VIEW,
    },
    {
        "sourcepath": _portletpath("SiteWindowPortlet.js"),
        "id": "SiteWindowPortlet",
        "title": "Site Window",
        "permission": ZEN_VIEW,
    },
    {
        "sourcepath": _portletpath("DeviceIssuesPortlet.js"),
        "id": "DeviceIssuesPortlet",
        "title": "Device Issues",
        "permission": ZEN_COMMON,
    },
    {
        "sourcepath": _portletpath("TopLevelOrgsPortlet.js"),
        "id": "TopLevelOrgsPortlet",
        "title": "Top Level Organizers",
        "permission": ZEN_VIEW,
    },
    {
        "sourcepath": _portletpath("WatchListPortlet.js"),
        "id": "WatchListPortlet",
        "title": "Watch List",
        "permission": ZEN_COMMON,
    },
    {
        "sourcepath": _portletpath("productionStatePortlet.js"),
        "id": "ProdStatePortlet",
        "title": "Production States",
        "permission": ZEN_COMMON,
    },
    {
        "sourcepath": _portletpath("userMessagesPortlet.js"),
        "id": "UserMsgsPortlet",
        "title": "Messages",
        "permission": ZEN_COMMON,
    },
]


def register_default_portlets(portletmanager):
    for portlet in portlets:
        if portletmanager.find(portlet["id"]) is None:
            portletmanager.register_portlet(**portlet)
