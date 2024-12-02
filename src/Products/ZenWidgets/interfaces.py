##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.container.interfaces import IContained, IContainer
from zope.interface import Interface, Attribute


class IMessage(IContained):
    """A single message.

    Messages are stored in user-specific MessageQueue objects and in the
    session object.
    """

    title = Attribute("Title of the message")
    body = Attribute("Body of the message")
    image = Attribute("Optional path to image to be displayed")
    priority = Attribute("Priority of the message")
    timestamp = Attribute("Time the message was sent")
    sticky = Attribute("Explicitly designate stickiness")

    def delete():
        """Delete this message from any queues in which it exists."""

    def mark_as_read():
        """Mark this message as read."""


class IMessageSender(Interface):
    """Something able to send messages."""

    def sendToBrowser(title, body, priority, image=None, sticky=None):
        """Create a message and store it on the request object."""

    def sendToUser(title, body, priority, image=None, user=None):
        """
        Create a message and store it in the L{IMessageQueue} of the user
        specified. If no user is specified, use the queue of the current user.
        """

    def sendToAll(title, body, priority, image=None):
        """
        For eash user in the system, create an identical message and store it
        in the user's L{IMessageQueue}.
        """


class IMessageQueue(IContainer):
    """Marker interface for a message container."""


class IMessageBox(Interface):
    """Something that can provide messages."""

    messagebox = Attribute("The source of IMessage objects.")

    def get_messages():
        """Return all messages."""

    def get_unread():
        """Return all messages that have not been marked as read."""


class IUserMessages(IMessageBox):
    """Object that is able to provide IMessage objects from a user queue."""


class IBrowserMessages(IMessageBox):
    """Object that is able to provide IMessage objects from the request."""
