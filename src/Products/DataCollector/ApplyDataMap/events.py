##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.interfaces import Interface, Attribute
from zope.interface import implementer


class IDatamapEvent(Interface):
    dmd = Attribute("a handle for dmd")  # pragma: no mutate
    objectmap = Attribute("an ObjectMap")  # pragma: no mutate
    target = Attribute(
        "The device or component the ObjectMap modifies"  # pragma: no mutate
    )


class IDatamapAddEvent(IDatamapEvent):
    pass


class IDatamapUpdateEvent(IDatamapEvent):
    pass


@implementer(IDatamapAddEvent)
class DatamapAddEvent(object):
    def __init__(self, dmd, objectmap, target):
        self.dmd = dmd
        self.objectmap = objectmap
        self.target = target


@implementer(IDatamapUpdateEvent)
class DatamapUpdateEvent(object):
    def __init__(self, dmd, objectmap, target):
        self.dmd = dmd
        self.objectmap = objectmap
        self.target = target


class IDatamapAppliedEvent(Interface):
    datamap = Attribute("a completed datamap")


@implementer(IDatamapAppliedEvent)
class DatamapAppliedEvent(object):
    def __init__(self, datamap):
        self.datamap = datamap
