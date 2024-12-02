##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import cgi
import time

from Products.CMFCore.utils import getToolByName
from zope.interface import implementer

from Products.ZenRelations.utils import ZenRelationshipNameChooser
from Products.ZenWidgets.interfaces import (
    IBrowserMessages,
    IMessage,
    IMessageBox,
    IMessageSender,
    IUserMessages,
)

# Constants representing priorities.
# Parallel definitions exist in zenoss.js.
INFO = 0
WARNING = 1
CRITICAL = 2


@implementer(IMessage)
class BrowserMessage(object):
    """A single message.

    Messages are stored on UserSettings and in the session object.
    """

    __parent__ = None
    title = None
    body = None
    timestamp = None
    priority = None
    _read = False

    def __init__(self, title, body, priority=INFO, image=None, sticky=None):
        """Initialize a BrowserMessage instance.

        @param title: The message title
        @type title: str
        @param body: The body of the message
        @type body: str
        @param priority: Message priority; one of INFO, WARNING, CRITICAL
        @type priority: int
        @param image: Optional URL of an image to be displayed in the message
        @type image: str
        """
        self.title = cgi.escape(title)
        self.body = body
        self.priority = priority
        self.image = image
        self.timestamp = time.time()
        self.sticky = sticky

    def delete(self):
        """Delete this message from the system.
        """
        self._read = True
        try:
            self.__parent__.remove(self)
        except (ValueError):
            pass
        del self

    def mark_as_read(self):
        self._read = True
        self.delete()


@implementer(IMessageBox)
class MessageBox(object):
    """Adapter for all persistent objects.

    Provides a method, L{get_messages}, that retrieves L{Message} objects.
    """

    messagebox = None

    def get_unread(self, min_priority=INFO):
        """Retrieve unread messages.

        @param min_priority: Optional minimum priority of messages to be
        returned; one of INFO, WARNING, CRITICAL
        @type min_priority: int
        @return: A list of objects implementing L{IMessage}.
        @rtype: list
        """
        msgs = self.get_messages(min_priority)
        msgs = filter(lambda x: not x._read, msgs)
        return msgs

    def get_messages(self, min_priority=INFO):
        """Retrieve messages from the current users's session object.

        @param min_priority: Optional minimum priority of messages to be
        returned; one of INFO, WARNING, CRITICAL
        @type min_priority: int
        @return: A list of L{Message} objects.
        @rtype: list
        """
        msgs = sorted(self.messagebox, key=lambda x: x.timestamp)
        msgs = filter(lambda x: x.priority >= min_priority, msgs)
        return msgs


@implementer(IBrowserMessages)
class BrowserMessageBox(MessageBox):
    """Adapter for all persistent objects.

    Provides a method, L{get_messages}, that retrieves L{Message} objects
    from the current user's session.
    """

    def __init__(self, context):
        """Initialize a BrowserMessageBox instance.

        @param context: The object being adapted. Must have access to the
            current request object via acquisition.
        @type context: Persistent
        """
        self.context = context
        self.messagebox = self.context.REQUEST.SESSION.get("messages", [])

    def get_unread(self, min_priority=INFO):
        msgs = super(BrowserMessageBox, self).get_unread(
            min_priority=min_priority
        )
        # force the session to persist
        if msgs:
            self.context.REQUEST.SESSION._p_changed = True
        return msgs


@implementer(IUserMessages)
class UserMessageBox(MessageBox):
    """Adapter for all persistent objects.

    Provides a method, L{get_messages}, that retrieves L{Message} objects
    from the current user's L{MessageQueue}.
    """

    def __init__(self, context, user=None):
        """Initialize a UserMessageBox instance.

        @param context: The object being adapted. Must have access to the dmd
            via acquisition.
        @type context: Persistent
        @param user: Optional username corresponding to the queue from which
            messages will be retrieved. If left as C{None}, the current
            user's queue will be used.
        @type user: str
        """
        self.context = context
        self.user = user
        users = getToolByName(self.context, "ZenUsers")
        us = users.getUserSettings(self.user)
        self.messagebox = us.messages()


@implementer(IMessageSender)
class MessageSender(object):
    """
    Adapts persistent objects in order to provide message sending capability.
    """

    def __init__(self, context):
        """Initialize a MessageSender instance.

        @param context: The object being adapted. Must have access to the
                        dmd and the current request object via acquisition.
        @type context: Persistent
        """
        self.context = context

    def sendToBrowser(
        self, title, body, priority=INFO, image=None, sticky=None
    ):
        """Create a message and store it on the session object.

        @param title: The message title
        @type title: str
        @param body: The body of the message
        @type body: str
        @param priority: Message priority; one of INFO, WARNING, CRITICAL
        @type priority: int
        @param image: Optional URL of an image to be displayed in the message
        @type image: str
        """
        context = self.context.REQUEST.SESSION.get("messages")
        if context is None:
            self.context.REQUEST.SESSION["messages"] = context = []
        m = BrowserMessage(title, body, priority, image, sticky)
        m.__parent__ = context
        context.append(m)
        self.context.REQUEST.SESSION._p_changed = True

    def sendToUser(self, title, body, priority=INFO, image=None, user=None):
        """
        Create a message and store it in the L{IMessageQueue} of the user
        specified. If no user is specified, use the queue of the current user.

        @param title: The message title
        @type title: str
        @param body: The body of the message
        @type body: str
        @param priority: Message priority; one of INFO, WARNING, CRITICAL
        @type priority: int
        @param image: Optional URL of an image to be displayed in the message
        @type image: str
        @param user: Optional username corresponding to the queue to which
                     messages should be sent. If left as C{None}, the current
                     user's queue will be used.
        @type user: str
        """
        users = getToolByName(self.context, "ZenUsers")
        us = users.getUserSettings(user)
        id = ZenRelationshipNameChooser(us.messages).chooseName("msg")
        # done in here to prevent recursive imports from ZenModelRM
        from PersistentMessage import PersistentMessage

        m = PersistentMessage(id, title, body, priority, image)
        us.messages._setObject(m.id, m)

    def sendToAll(self, title, body, priority=INFO, image=None):
        """
        For eash user in the system, create an identical message and store it
        in the user's L{IMessageQueue}.

        @param title: The message title
        @type title: str
        @param body: The body of the message
        @type body: str
        @param priority: Message priority; one of INFO, WARNING, CRITICAL
        @type priority: int
        @param image: Optional URL of an image to be displayed in the message
        @type image: str
        """
        users = getToolByName(self.context, "ZenUsers")
        for name in users.getAllUserSettingsNames():
            self.sendToUser(title, body, priority, user=name, image=image)


class ScriptMessageSender(MessageSender):
    """Special message sender for use in scripts.

    Short-circuits sendToBrowser and sendToUser, since they don't really
    apply. sendToAll should still work fine though.
    """

    def sendToBrowser(
        self, title, body, priority=INFO, image=None, sticky=None
    ):
        pass

    def sendToUser(self, title, body, priority=INFO, image=None, user=None):
        pass
