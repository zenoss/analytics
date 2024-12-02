##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
This is in a separate module to prevent recursive import.
"""

import cgi
import time

from zope.interface import implementer

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import ToManyCont, ToOne

from .interfaces import IMessage
from .messaging import INFO


@implementer(IMessage)
class PersistentMessage(ZenModelRM):
    """A single message.

    Messages are stored as relations on UserSettings and in the session object.
    """

    _relations = (
        (
            "messageQueue",
            ToOne(
                ToManyCont,
                "Products.ZenModel.UserSettings.UserSettings",
                "messages",
            ),
        ),
    )

    title = None
    body = None
    timestamp = None
    priority = None
    _read = False

    def __init__(self, id, title, body, priority=INFO, image=None):
        """Initialize an PersistentMessage instance.

        @param title: The message title
        @type title: str
        @param body: The body of the message
        @type body: str
        @param priority: Message priority; one of INFO, WARNING, CRITICAL
        @type priority: int
        @param image: Optional URL of an image to be displayed in the message
        @type image: str
        """
        super(PersistentMessage, self).__init__(id)
        self.title = cgi.escape(title)
        self.body = cgi.escape(body)
        self.priority = priority
        self.image = image
        self.timestamp = time.time()

    def mark_as_read(self):
        """Mark this message as read."""
        self._read = True

    def delete(self):
        """Delete this message from the system."""
        self.__primary_parent__._delObject(self.id)
