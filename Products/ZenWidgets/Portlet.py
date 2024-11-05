##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from os.path import basename, exists
from string import Template

from AccessControl.class_init import InitializeClass

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import ZEN_COMMON
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.Portlet")


def manage_addPortlet(self, context, REQUEST=None):
    """Add a portlet."""


class Portlet(ZenModelRM):
    """
    A wrapper for a portlet javascript source file that can include metadata
    such as a name, a title, a description and permissions.

    Portlets should not be instantiated directly. They should only be created
    by a PortletManager object.
    """

    source = ""
    height = 200

    portal_type = meta_type = "Portlet"

    _relations = (
        (
            "portletManager",
            ToOne(
                ToManyCont, "Products.ZenWidgets.PortletManager", "portlets"
            ),
        ),
    )

    _properties = (
        {"id": "title", "type": "string", "mode": "w"},
        {"id": "description", "type": "string", "mode": "w"},
        {"id": "permission", "type": "string", "mode": "w"},
        {"id": "sourcepath", "type": "string", "mode": "w"},
        {"id": "preview", "type": "string", "mode": "w"},
        {"id": "height", "type": "int", "mode": "w"},
    )

    def __init__(
        self,
        sourcepath,
        id="",
        title="",
        description="",
        preview="",
        height=200,
        permission=ZEN_COMMON,
    ):
        if not id:
            id = basename(sourcepath).split(".")[0]
        self.id = id
        ZenModelRM.__init__(self, id)
        self.title = title
        self.description = description
        self.permission = permission
        self.sourcepath = sourcepath
        self.preview = preview
        self.height = height
        self._read_source()

    def _getSourcePath(self):
        return zenPath(self.sourcepath)

    def check(self):
        return exists(self._getSourcePath())

    def _read_source(self):
        try:
            path = (
                self.sourcepath
                if exists(self.sourcepath)
                else self._getSourcePath()
            )
            f = file(path)
        except IOError as ex:
            log.error("Unable to load portlet from '%s': %s", path, ex)
            return
        else:
            tvars = {
                "portletId": self.id,
                "portletTitle": self.title,
                "portletHeight": self.height,
            }
            self.source = Template(f.read()).safe_substitute(tvars)
            f.close()

    def getPrimaryPath(self, fromNode=None):
        """Override the default, which doesn't account for things on zport."""
        return ("", "zport") + super(Portlet, self).getPrimaryPath(fromNode)

    def get_source(self, debug_mode=False):
        if debug_mode:
            self._read_source()
        src = []
        src.append(self.source)
        src.append(
            "YAHOO.zenoss.portlet.register_portlet('%s', '%s');"
            % (self.id, self.title)
        )
        return "\n".join(src)


InitializeClass(Portlet)
