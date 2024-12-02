##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import (
    ZopeTwoPageTemplateFile,
    ViewPageTemplateFile,
)

from Products import Zuul
from Products.ZenUtils.controlplane.application import getConnectionSettings
from Products.ZenUtils.controlplane.client import ControlPlaneClient
from Products.ZenUtils.Utils import getPasswordFields, maskSecureProperties
from Products.Zuul.interfaces import IInfo
from Products.Zuul.routers.device import DeviceRouter
from Products.Zuul.routers.nav import DetailNavRouter

log = logging.getLogger("zen.browser.pages")


class DaemonsView(BrowserView):

    page = ViewPageTemplateFile("templates/daemons.pt")

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.cc_version = ""

    def __call__(self):
        return self.render()

    def render(self):
        self._doCCLogin()
        return self.page()

    def _doCCLogin(self):
        """
        The daemons page makes calls to logstash's elasticsearch, which is
        protected via CC credentials.  This is a helper method to authenticate
        with CC, and set a cookie in the user's browser.
        """
        cpClient = ControlPlaneClient(**getConnectionSettings())
        self.cc_version = cpClient.cc_version
        cookies = None
        try:
            cookies = cpClient.cookies()
        except Exception:
            log.warn(
                "Unable to log into Control Center, "
                "log viewing functionality may be impacted"
            )
            return
        for cookie in cookies:
            self.request.response.setCookie(
                name=cookie["name"],
                value=cookie["value"],
                quoted=True,
                domain=self.request.environ["HTTP_HOST"].split(":")[
                    0
                ],  # Don't include the port
                path="/",
                secure=cookie["secure"],
            )


class ITInfrastructure(BrowserView):

    __call__ = ZopeTwoPageTemplateFile("templates/itinfrastructure.pt")

    def getTrees(self):
        router = DeviceRouter(self.context.dmd, {})
        method = router.getTree
        settings = (
            self.context.dmd.UserInterfaceSettings.getInterfaceSettings()
        )
        if settings["incrementalTreeLoad"]:
            method = router.asyncGetTree
        deviceTree = method("/zport/dmd/Devices")
        # system
        systemTree = method("/zport/dmd/Systems")
        # groups
        groupTree = method("/zport/dmd/Groups")
        # location
        locTree = method("/zport/dmd/Locations")
        js = """
             Zenoss.env.device_tree_data = %s;
             Zenoss.env.system_tree_data = %s;
             Zenoss.env.group_tree_data = %s;
             Zenoss.env.location_tree_data = %s;
        """ % (
            json.dumps(deviceTree),
            json.dumps(systemTree),
            json.dumps(groupTree),
            json.dumps(locTree),
        )
        return js


class DeviceDetails(BrowserView):

    __call__ = ZopeTwoPageTemplateFile("templates/devdetail.pt")

    def getComponentTree(self):
        router = DeviceRouter(self.context.dmd, {})
        uid = self.context.getPrimaryId()
        tree = router.getComponentTree(uid)
        js = """
            Zenoss.env.componentTree = %s;
        """ % json.dumps(
            tree
        )
        return js

    def fetchLeftHandMenu(self):
        router = DetailNavRouter(self.context.dmd, {})
        menuIds = ["More", "Add", "TopLevel", "Manage"]
        uid = self.context.getPrimaryId()
        response = router.getDetailNavConfigs(uid=uid, menuIds=menuIds)
        js = """
            Zenoss.env.lefthandnav = %s;
        """ % json.dumps(
            response.data
        )
        return js

    def getInfoObject(self):
        info = IInfo(self.context)
        # links is very expensive so do not marshal that
        keys = [
            key
            for key in dir(info)
            if (
                not key.startswith("_")
                and key not in ("links", "uptime", "events", "deviceClass")
                and not callable(getattr(info, key))
            )
        ]
        secure_properties = getPasswordFields(info)
        data = Zuul.marshal(info, keys)
        maskSecureProperties(data, secure_properties)
        response = dict(data=data)
        js = """
            Zenoss.env.infoObject = %s;
        """ % (
            json.dumps(response)
        )
        return js
