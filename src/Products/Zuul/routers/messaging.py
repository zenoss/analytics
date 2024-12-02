##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Operations for Messaging.

Available at:  /zport/dmd/messaging_router
"""
from Persistence import PersistentMapping
from ZODB.transact import transact
from Products.ZenUtils.Ext import DirectRouter
#from Products.ZenModel.ZenossSecurity import *
from Products.ZenWidgets.interfaces import IUserMessages, IBrowserMessages
from Products.ZenWidgets import messaging


class MessagingRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on messages
    """
    @transact
    def setBrowserState(self, state):
        """
        Save the browser state for the current user.

        @param state: The browser state as a JSON-encoded string
        @type state: str
        """
        userSettings = self.context.dmd.ZenUsers.getUserSettings()
        state_container = getattr(userSettings, '_browser_state', None)
        if isinstance(state_container, basestring) or state_container is None:
            state_container = PersistentMapping()
            userSettings._browser_state = state_container
        if state != state_container.get('state', ''):
            state_container['state'] = state


    def clearBrowserState(self, user=None):
        """
        Removes all the stored state associated with the current user
        """
        if user:
            userSettings = self.context.dmd.ZenUsers._getOb(user)
        else:
            userSettings = self.context.dmd.ZenUsers.getUserSettings()
        if getattr(userSettings, '_browser_state', None):
            del userSettings._browser_state
        messaging.IMessageSender(self.context).sendToBrowser(
            'Preferences Reset',
            'Preferences reset to their default values.',
            priority=messaging.WARNING
            )

    def getUserMessages(self):
        """
        Get the queued messages for the logged in user.

        @rtype:   dictionary
        @return:  B{Properties}:
           - messages: ([string]) A list of queued messages.
        """
        # user messages are stored in the logged in users "usersettings" object
        # which must be able to access ZenUsers (off of dmd)
        messages = IUserMessages(self.context.zport.dmd).get_unread()
        messages.extend(IBrowserMessages(self.context).get_unread())
        messages.sort(key=lambda x:x.timestamp)
        result = []
        for message in messages:
            result.append(dict(
                sticky = True if message.priority >= messaging.CRITICAL else False,
                image = message.image,
                title = message.title,
                body = message.body,
                priority = message.priority
            ))
            message.mark_as_read()

        return {
            'messages': result
        }
