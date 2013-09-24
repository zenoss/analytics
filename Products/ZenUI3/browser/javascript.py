##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os
import Globals
import zope.interface
import md5
from interfaces import IMainSnippetManager
from Products.ZenUI3.utils.javascript import JavaScriptSnippetManager,\
    JavaScriptSnippet, SCRIPT_TAG_TEMPLATE
from Products.ZenUI3.browser.interfaces import IJavaScriptSrcViewlet,\
    IJavaScriptBundleViewlet, IJavaScriptSrcManager
from Products.Five.viewlet.viewlet import ViewletBase
from Products.ZenUI3.navigation.manager import WeightOrderedViewletManager
from Products.ZenUtils.extdirect.zope.metaconfigure import allDirectRouters
from zope.publisher.browser import TestRequest
from zope.component import getAdapter
from Products.ZenModel.ZVersion import VERSION
from Products.Zuul.decorators import memoize

dummyRequest = TestRequest()

@memoize
def getPathModifiedTime(path):
    """
    This method takes a js request path such as /++resources++zenui/zenoss/file.js and
    returns the last time the file was modified.
    """
    if "++resource++" in path:
        identifier = path.split('/')[1].replace("++resource++", "")
        filePath = path.replace("/++resource++" + identifier , "")
        resource = getAdapter(dummyRequest, name=identifier)
        fullPath = resource.context.path + filePath
        if os.path.exists(fullPath):
            return os.path.getmtime(fullPath)

SCRIPT_TAG_SRC_TEMPLATE = '<script type="text/javascript" src="%s"></script>\n'


def getVersionedPath(path):
    token = getPathModifiedTime(path) or VERSION
    return '%s?v=%s' % (path, token)

class MainSnippetManager(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """
    zope.interface.implements(IMainSnippetManager)


class JavaScriptSrcManager(WeightOrderedViewletManager):
    zope.interface.implements(IJavaScriptSrcManager)


class JavaScriptSrcViewlet(ViewletBase):
    zope.interface.implements(IJavaScriptSrcViewlet)
    path = None

    def render(self):
        val = None
        if self.path:
            val = SCRIPT_TAG_SRC_TEMPLATE % getVersionedPath(self.path)
        return val


class JavaScriptSrcBundleViewlet(ViewletBase):
    zope.interface.implements(IJavaScriptBundleViewlet)
    #space delimited string of src paths
    paths = ''

    def render(self):
        vals = []
        if self.paths:
            for path in self.paths.split():
                vals.append(SCRIPT_TAG_SRC_TEMPLATE % getVersionedPath(path))
        js = ''
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
            routernames = sorted([r['name'] for r in allDirectRouters.values()])
            self.directHash = md5.new(" ".join(routernames)).hexdigest()
        path = self.path  + "?v=" + self.directHash
        return SCRIPT_TAG_SRC_TEMPLATE % path

class ZenossAllJs(JavaScriptSrcViewlet):
    zope.interface.implements(IJavaScriptSrcViewlet)

    def render(self):
        token = getPathModifiedTime("/++resource++zenui/js/deploy/zenoss-compiled.js") or VERSION
        path = "%s?v=%s" %("zenoss-all.js", token)
        return SCRIPT_TAG_SRC_TEMPLATE % (path)


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
        return  SCRIPT_TAG_TEMPLATE % js



class VisualizationInit(JavaScriptSnippet):
    """
    Performs necessary initialization for the visualization library
    """
    def snippet(self):
        js = """
            zenoss.visualization.url = window.location.protocol + "//" + window.location.host;
            zenoss.visualization.debug = false;
        """
        return  SCRIPT_TAG_TEMPLATE % js


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
        collectors = [[s] for s in self.context.dmd.Monitors.getPerformanceMonitorNames()]

        # priorities
        priorities = [dict(name=s[0],
                           value=int(s[1])) for s in
                      self.context.dmd.getPriorityConversions()]

        # production states
        productionStates = [dict(name=s[0],
                                 value=int(s[1])) for s in
                            self.context.dmd.getProdStateConversions()]

        snippet = """
            Zenoss.env.COLLECTORS = %r;
            Zenoss.env.priorities = %r;
            Zenoss.env.productionStates = %r;
        """ % ( collectors, priorities, productionStates )
        return snippet

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
            return ''
        state_container = getattr(userSettings, '_browser_state', {})
        if isinstance(state_container, basestring):
            state_container = {}
        state = state_container.get('state', '{}')
        return 'Ext.state.Manager.getProvider().setState(%r);' % state
