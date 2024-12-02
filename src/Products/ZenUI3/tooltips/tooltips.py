##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os.path
import re

from xml.dom import minidom

from Products.Five.browser import BrowserView
from zope import component
from zope.i18n.negotiator import negotiator
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.ZenUI3.navigation import getSelectedNames
from Products.ZenUI3.tooltips.interfaces import ITooltipProvider
from Products.ZenUtils.jsonutils import json

log = logging.getLogger("zen.tooltips")

_datapath = os.path.join(os.path.dirname(__file__), "data")
_valpat = re.compile(r"<[^<>]+>(.*)</[^<>]+>", re.M | re.S)
_tipattrs = {
    "showDelay": float,
    "hideDelay": float,
    "dismissDelay": float,
    "trackMouse": bool,
    "anchorToTarget": bool,
    "anchorOffset": int,
    "minWidth": int,
    "maxWidth": int,
    "shadow": str,
    "defaultAlign": str,
    "autoRender": bool,
    "quickShowInterval": int,
    "frame": bool,
    "hidden": bool,
    "baseCls": str,
    "autoHeight": bool,
    "closeAction": str,
    "title": str,
    "html": str,
    "target": str,
    "closable": bool,
    "anchor": str,
    "autoHide": bool,
}


def catalog_required(fn):
    """A decorator to be used around _TooltipCatalog functions that require
    its _catalog to be built.  A glorified way of lazy-loading the catalog to
    make sure zcml is fully loaded beforehand.
    """

    def inner(*args, **kwargs):
        if not args[0]._reloaded:
            args[0].reload()
        return fn(*args, **kwargs)

    return inner


class _TooltipCatalog(object):
    """
    Store the data pulled in from XML. This is a singleton and should not be
    instantiated directly.
    """

    _catalog = None

    def __init__(self):
        self._catalog = {}
        self._reloaded = False

    def add(self, lang, view, tip):
        self._catalog.setdefault(view, {}).setdefault(lang, []).append(tip)

    def _add_navhelp(self, lang, target, title, tip):
        d = {"title": title, "tip": tip}
        self._catalog.setdefault("nav-help", {}).setdefault(lang, {})[
            target
        ] = d

    def reload(self):
        """
        Read in tooltips from XML files.
        """

        def _load_tips(doc, lang, view):
            for tip in doc.getElementsByTagName("tooltip"):
                d = {}
                for node in tip.childNodes:
                    if isinstance(node, minidom.Text):
                        continue
                    result = _valpat.search(node.toxml())
                    if result:
                        value = result.groups()[0].strip()
                        name = node.tagName
                        if name in _tipattrs and _tipattrs[name] != str:
                            value = eval(value)
                        if isinstance(value, basestring):
                            value = value.replace("%26", "&")
                        d[name] = value
                if "autoHide" in d:
                    d["closable"] = not d["autoHide"]
                self.add(lang, view, d)

        def _load_navhelp(doc, lang):
            for tip in doc.getElementsByTagName("pagehelp"):
                result = _valpat.search(tip.toxml())
                target = tip.getAttribute("target")
                title = tip.getAttribute("title")
                if result and target:
                    value = result.groups()[0].strip()
                    self._add_navhelp(lang, target, title, value)

        def _load_files(_none, path, fnames):
            lang = path.rsplit("/", 1)[-1]
            for f in fnames:
                if not f.endswith(".xml"):
                    continue
                view = f[:-4]
                fd = open(os.path.join(path, f))
                data = fd.read()
                fd.close()
                doc = minidom.parseString(data.replace("&", "%26"))
                if f.startswith("nav-help"):
                    _load_navhelp(doc, lang)
                else:
                    _load_tips(doc, lang, view)
                doc.unlink()

        os.path.walk(_datapath, _load_files, None)

        # Now load up other tooltips.  The last one to override wins.
        # Processed by name in alphabetical order
        for name, klass in sorted(
            component.getUtilitiesFor(ITooltipProvider), key=lambda tup: tup[0]
        ):
            log.debug("Loading tooltip provider %s (%s)", name, klass)
            os.path.walk(klass().path(), _load_files, None)
        self._reloaded = True

    @catalog_required
    def tips(self, view, lang="en"):
        """
        Look up the tooltips for a given screen and language.
        """
        return self._catalog.get(view, {}).get(lang, [])[:]

    @catalog_required
    def pagehelp(self, navitem, lang="en"):
        """
        Look up the page-level help for a given screen and language.
        """
        return (
            self._catalog.get("nav-help", {}).get(lang, {}).get(navitem, None)
        )

    @catalog_required
    def langs(self, view):
        """
        Returns a list of languages available for a given screen.
        """
        return self._catalog.get(view, {}).keys()


TooltipCatalog = _TooltipCatalog()


class Tooltips(BrowserView):
    def __call__(self):
        results = []
        viewname = self.request["HTTP_REFERER"].rsplit("/", 1)[-1]
        # incase there are query parameters in the url
        if "?" in viewname:
            viewname = viewname.split("?")[0]
        lang = negotiator.getLanguage(
            TooltipCatalog.langs(viewname), self.request
        )
        tips = TooltipCatalog.tips(viewname, lang)
        tpl = "Zenoss.registerTooltip(%s);"
        for tip in tips:
            results.append(tpl % json(tip))
        # Bypass caching because all tooltips for all pages use the same
        # file tooltips.js
        self.request.response.setHeader("Pragma", "no-cache")
        self.request.response.setHeader("Cache-Control", "no-cache")
        self.request.response.setHeader("Content-Type", "text/javascript")
        return "Ext.onReady(function(){%s})" % "\n".join(results)


class PageLevelHelp(BrowserView):
    __call__ = ViewPageTemplateFile("pagehelp.pt")

    def __init__(self, context, request):
        super(PageLevelHelp, self).__init__(context, request)
        primary, secondary = getSelectedNames(self)
        lang = negotiator.getLanguage(
            TooltipCatalog.langs("nav-help"), self.request
        )
        self.tip = TooltipCatalog.pagehelp(primary, lang)
