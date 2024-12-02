##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.interface import implementer

from Products.ZenModel.DeviceOrganizer import DeviceOrganizer

from .interfaces import (
    IDeviceClassMoveEvent,
    IMessagePostPublishingEvent,
    IMessagePrePublishingEvent,
    IObjectAddedToOrganizerEvent,
    IObjectRemovedFromOrganizerEvent,
)

log = logging.getLogger("zen.modelchanges")


@implementer(IObjectAddedToOrganizerEvent)
class ObjectAddedToOrganizerEvent(object):
    """
    When an object is added to a new organizer
    """

    def __init__(self, object, organizer):
        self.object = object
        if not isinstance(organizer, DeviceOrganizer):
            raise TypeError(
                " %s is not an instance of Device Organizer" % organizer
            )
        self.organizer = organizer


@implementer(IObjectRemovedFromOrganizerEvent)
class ObjectRemovedFromOrganizerEvent(object):
    """
    When an object is removed from an organizer
    """

    def __init__(self, object, organizer):
        self.object = object
        if not isinstance(organizer, DeviceOrganizer):
            raise TypeError(
                " %s is not an instance of Device Organizer" % organizer
            )
        self.organizer = organizer


@implementer(IDeviceClassMoveEvent)
class DeviceClassMovedEvent(object):
    """
    Fired when a device moves from a class to another
    """

    def __init__(self, object, fromOrganizer, toOrganizer):
        self.object = object
        self.fromOrganizer = fromOrganizer
        self.toOrganizer = toOrganizer


@implementer(IMessagePrePublishingEvent)
class MessagePrePublishingEvent(object):
    """
    Fired just before a batch of ModelChangeList messages is published to
    Rabbit.
    """

    def __init__(self, msgs, maintWindowChanges, refs=None):
        self.msgs = msgs
        self.refs = refs
        if self.refs is None:
            self.refs = []
        # list of guids changed because of maintWindow (prodState only)
        self.maintWindowChanges = maintWindowChanges


@implementer(IMessagePostPublishingEvent)
class MessagePostPublishingEvent(object):
    """
    Fired after transaction completion.
    """


    def __init__(self, refs=None):
        self.refs = refs
        if self.refs is None:
            self.refs = []
