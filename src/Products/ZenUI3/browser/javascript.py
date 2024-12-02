##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import md5
import os

from urlparse import urljoin

import Globals
import six
import zope.interface

from Products.Five.viewlet.viewlet import ViewletBase
from zope.publisher.browser import TestRequest
from zope.component import getAdapter

from Products.ZenUI3.browser.interfaces import (
    ICSSBundleViewlet,
    ICSSSrcManager,
    IJavaScriptBundleViewlet,
    IJavaScriptSrcManager,
    IJavaScriptSrcViewlet,
    IXTraceSrcManager,
)
from Products.ZenUI3.navigation.manager import WeightOrderedViewletManager
from Products.ZenUI3.utils.javascript import (
    JavaScriptSnippet,
    JavaScriptSnippetManager,
    SCRIPT_TAG_TEMPLATE,
)
from Products.ZenUtils.extdirect.zope.metaconfigure import allDirectRouters
from Products.ZenUtils.Utils import monkeypatch
from Products.Zuul.decorators import memoize

from .interfaces import IMainSnippetManager
from .resources import hasCompiledJavascript


dummyRequest = TestRequest()

# this will contained every registered resource directory
_registered_resources = []


@monkeypatch("Products.Five.browser.metaconfigure")
def resourceDirectory(*args, **kwargs):
    """
    There isn't a way to ask the site manager for a list of registered
    resource directories and since they are defined in zenpacks we don't
    know the list ahead of time.
    This is used so we can look for JS test files instead of requiring each one
    to be explicitly registered somehow.
    """
    global _registered_resources
    # will be name and directory
    _registered_resources.append(kwargs)
    return original(*args, **kwargs)  # noqa F821


def getAllZenPackResources():
    # make a copy so the original isn't mutated
    return [
        x for x in _registered_resources if "zenpack" in x["directory"].lower()
    ]


@memoize
def getPathModifiedTime(path):
    """
    This method takes a js request path such as
    /++resources++zenui/zenoss/file.js and
    returns the last time the file was modified.
    """
    if "++resource++" in path:
        identifier = path.split("/")[1].replace("++resource++", "")
        filePath = path.replace("/++resource++" + identifier, "")
        resource = getAdapter(dummyRequest, name=identifier)
        fullPath = resource.context.path + filePath
        if os.path.exists(fullPath):
            return os.path.getmtime(fullPath)


SCRIPT_TAG_SRC_TEMPLATE = '<script type="text/javascript" src="%s"></script>\n'
LINK_TAG_SRC_TEMPLATE = (
    '<link rel="stylesheet" type="text/css" href="%s"></link>\n'
)


def absolutifyPath(path):
    return urljoin("/zport/dmd", path)


getVersionedPath = absolutifyPath


class MainSnippetManager(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """

    zope.interface.implements(IMainSnippetManager)


class CSSSrcManager(WeightOrderedViewletManager):
    zope.interface.implements(ICSSSrcManager)


class JavaScriptSrcManager(WeightOrderedViewletManager):
    zope.interface.implements(IJavaScriptSrcManager)


class XTraceSrcManager(WeightOrderedViewletManager):
    zope.interface.implements(IXTraceSrcManager)


class CSSSrcBundleViewlet(ViewletBase):
    zope.interface.implements(ICSSBundleViewlet)
    # space delimited string of src paths
    paths = ""

    def render(self):
        vals = []
        if self.paths:
            for path in self.paths.split():
                vals.append(LINK_TAG_SRC_TEMPLATE % absolutifyPath(path))
        js = ""
        if vals:
            js = "".join(vals)
        return js


class JavaScriptSrcViewlet(ViewletBase):
    zope.interface.implements(IJavaScriptSrcViewlet)
    path = None

    def render(self):
        if not self.path:
            return
        return SCRIPT_TAG_SRC_TEMPLATE % absolutifyPath(self.path)


class JavaScriptSrcBundleViewlet(ViewletBase):
    zope.interface.implements(IJavaScriptBundleViewlet)
    # space delimited string of src paths
    paths = ""

    def render(self):
        vals = []
        if self.paths:
            for path in self.paths.split():
                vals.append(SCRIPT_TAG_SRC_TEMPLATE % absolutifyPath(path))
        js = ""
        if vals:
            js = "".join(vals)
        return js


class ExtDirectViewlet(JavaScriptSrcViewlet):
    """
    A specialized renderer for ExtDirect. We can not cache-bust this
    file by the modified time so we use a hash of the defined routers
    """

    directHash = None

    def render(self):
        if self.directHash is None:
            # append the extdirect request with a hash or all routers
            # so that it is updated when a new zenpack is installed
            routernames = sorted(
                [r["name"] for r in allDirectRouters.values()]
            )
            self.directHash = md5.new(" ".join(routernames)).hexdigest()
        path = self.path + "?v=" + self.directHash
        return SCRIPT_TAG_SRC_TEMPLATE % path


class ZenossAllJs(JavaScriptSrcViewlet):
    """
    When Zope is in debug mode, we want to use the development JavaScript
    source files, so we don't have to make changes to a single huge file.
    If Zope is in production mode and the compressed file is not available,
    we will use the source files instead of just giving up.
    """

    zope.interface.implements(IJavaScriptSrcViewlet)

    def update(self):
        if Globals.DevelopmentMode or not hasCompiledJavascript():
            # Use the view that creates concatenated js on the fly from disk
            self.path = "/zport/dmd/zenoss-all.js"
        else:
            # Use the compiled javascript
            self.path = "/++resource++zenui/deploy/zenoss-compiled.js"


class ExtAllJs(JavaScriptSrcViewlet):
    zope.interface.implements(IJavaScriptSrcViewlet)
    path = None

    def update(self):
        if Globals.DevelopmentMode:
            self.path = "/++resource++extjs/ext-all-dev.js"
        else:
            self.path = "/++resource++extjs/ext-all.js"


class FireFoxExtCompat(JavaScriptSnippet):
    def snippet(self):
        js = """
         (function() {
            var ua = navigator.userAgent.toLowerCase();
            if (ua.indexOf("firefox/3.6") > -1) {
                Ext.toArray = function(a, i, j, res) {
                    res = [];
                    Ext.each(a, function(v) { res.push(v); });
                    return res.slice(i || 0, j || res.length);
                }
            }
        })();
        """
        return SCRIPT_TAG_TEMPLATE % js


class VisualizationInit(JavaScriptSnippet):
    """
    Performs necessary initialization for the visualization library
    """

    def snippet(self):
        js = """
            if (window.zenoss !== undefined) {
                zenoss.visualization.url = window.location.protocol + "//" + window.location.host;
                zenoss.visualization.debug = false;
            }
        """  # noqa E501
        return SCRIPT_TAG_TEMPLATE % js


class ZenossSettings(JavaScriptSnippet):
    """
    Renders client side settings.
    """

    def snippet(self):
        settings = self.context.dmd.UserInterfaceSettings
        js = ["Ext.namespace('Zenoss.settings');"]
        for name, value in settings.getInterfaceSettings().iteritems():
            js.append("Zenoss.settings.%s = %s;" % (name, str(value).lower()))
        return "\n".join(js)


class ZenossData(JavaScriptSnippet):
    """
    This preloads some data for the UI so that every page doesn't have to send
    a separate router request to fetch it.
    """

    def snippet(self):
        # collectors
        collectors = [
            [s] for s in self.context.dmd.Monitors.getPerformanceMonitorNames()
        ]

        # priorities
        priorities = [
            {"name": s[0], "value": int(s[1])}
            for s in self.context.dmd.getPriorityConversions()
        ]

        # production states
        productionStates = [
            {"name": s[0], "value": int(s[1])}
            for s in self.context.dmd.getProdStateConversions()
        ]

        # timezone
        # to determine the timezone we look in the following order
        # 1. What the user has saved
        # 2. The timezone of the server
        # 3. the timezone of the browser
        user = self.context.dmd.ZenUsers.getUserSettings()
        timezone = user.timezone
        date_fmt = user.dateFormat
        time_fmt = user.timeFormat
        snippet = """
          (function(){
            Ext.namespace('Zenoss.env');

            Zenoss.env.COLLECTORS = %r;
            Zenoss.env.priorities = %r;
            Zenoss.env.productionStates = %r;
            Zenoss.USER_TIMEZONE = "%s" || jstz.determine().name();
            Zenoss.USER_DATE_FORMAT = "%s" || "YYYY/MM/DD";
            Zenoss.USER_TIME_FORMAT = "%s" || "HH:mm:ss";
          })();
        """ % (
            collectors,
            priorities,
            productionStates,
            timezone,
            date_fmt,
            time_fmt,
        )
        return SCRIPT_TAG_TEMPLATE % snippet


class BrowserState(JavaScriptSnippet):
    """
    Restores the browser state.
    """

    def snippet(self):
        try:
            userSettings = self.context.ZenUsers.getUserSettings()
        except AttributeError:
            # We're on a backcompat page where we don't have browser state
            # anyway. Move on.
            return ""
        state_container = getattr(userSettings, "_browser_state", {})
        if isinstance(state_container, six.string_types):
            state_container = {}
        state = state_container.get("state", "{}")
        return "Ext.state.Manager.getProvider().setState(%r);" % state
