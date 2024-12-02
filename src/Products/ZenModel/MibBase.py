##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.interface import implementer

from .interfaces import IIndexed
from .ZenModelRM import ZenModelRM
from .ZenPackable import ZenPackable


@implementer(IIndexed)
class MibBase(ZenModelRM, ZenPackable):
    default_catalog = "mibSearch"

    _relations = ZenPackable._relations[:]

    moduleName = ""
    nodetype = ""
    oid = ""
    status = ""
    description = ""

    _properties = (
        {"id": "moduleName", "type": "string", "mode": "w"},
        {"id": "nodetype", "type": "string", "mode": "w"},
        {"id": "oid", "type": "string", "mode": "w"},
        {"id": "status", "type": "string", "mode": "w"},
        {"id": "description", "type": "string", "mode": "w"},
    )

    def __init__(self, id, title="", **kwargs):
        super(ZenModelRM, self).__init__(id, title)
        atts = self.propertyIds()
        for key, val in kwargs.items():
            if key in atts:
                setattr(self, key, val)

    def getFullName(self):
        """Return full value name in form MODULE::attribute."""
        return "%s::%s" % (self.moduleName, self.id)

    def summary(self):
        """Return summary string for Mib objects."""
        return [
            str(getattr(self, p))
            for p in self.propertyIds()
            if str(getattr(self, p))
        ]
