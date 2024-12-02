##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import sys

from glob import glob

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import ZEN_COMMON
from Products.ZenUtils.Utils import importClass

from . import plugins

log = logging.getLogger("zen.reportserver")


class ReportServer(ZenModelRM):
    """A front end to all the report plugins."""

    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

    def _getPluginDirectories(self):
        directories = []
        for p in self.dmd.ZenPackManager.packs():
            if p.id == "broken":
                continue
            try:
                pluginpath = p.path("reports", "plugins")
                directories.append(pluginpath)
            except AttributeError:
                log.warn("Unable to load report plugins for ZenPack %s", p.id)
        directories.append(plugins.__path__[0])
        return directories

    def listPlugins(self):
        allPlugins = []
        for dirpath in self._getPluginDirectories():
            allPlugins.extend(
                fn.replace(".py", "")
                for fn in glob("%s/*.py" % dirpath)
                if not fn.endswith("__init__.py")
            )
        return allPlugins

    def _importPluginClass(self, name):
        """
        Find the named plugin and import it.
        """
        klass = None
        if name.startswith("/"):
            if name.endswith(".py"):
                name = name.replace(".py", "")
            if os.path.exists(name + ".py"):
                try:
                    d, name = name.rsplit("/", 1)
                    sys.path.insert(0, d)
                    klass = importClass(name)
                finally:
                    sys.path.remove(d)
        else:
            for d in self._getPluginDirectories():
                if os.path.exists("%s/%s.py" % (d, name)):
                    try:
                        sys.path.insert(0, d)
                        klass = importClass(name)
                        break
                    finally:
                        sys.path.remove(d)
        return klass

    security.declareProtected(ZEN_COMMON, "plugin")

    def plugin(self, name, REQUEST, templateArgs=None):
        "Run a plugin to generate the report object"
        dmd = self.dmd
        args = dict(zip(REQUEST.keys(), REQUEST.values()))

        # We don't want the response object getting passed to the plugin
        # because if it is stringified, it can modify the return code
        # and cause problems upstream.
        if "RESPONSE" in args:
            del args["RESPONSE"]
        klass = self._importPluginClass(name)
        if not klass:
            raise IOError('Unable to find plugin named "%s"' % name)
        instance = klass()
        log.debug("Running plugin %s", name)
        try:
            if templateArgs is None:
                return instance.run(dmd, args)
            return instance.run(dmd, args, templateArgs)
        except Exception:
            log.exception("Failed to run plugin %s (%s)", name, instance)
            return []
        finally:
            # abort the current transaction so long running reports do not
            # cause a conflict
            self._p_jar.sync()


def manage_addReportServer(context, id, REQUEST=None):
    """make a ReportServer"""
    rs = ReportServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )


InitializeClass(ReportServer)
