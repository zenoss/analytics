##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.Five.browser import BrowserView

from Products.ZenUtils.jsonutils import json

from .. import messaging
from ..interfaces import IBrowserMessages, IUserMessages


class UserMessages(BrowserView):
    """
    Delivers up user messages for the current user to the client-side
    YAHOO.zenoss.Messenger.
    """

    @json
    def __call__(self):
        messages = IUserMessages(self.context).get_unread()
        messages.extend(IBrowserMessages(self.context).get_unread())
        messages.sort(key=lambda x: x.timestamp)
        result = []
        for message in messages:
            result.append(
                dict(
                    sticky=message.priority >= messaging.CRITICAL
                    and True
                    or False,
                    image=message.image,
                    title=message.title,
                    body=message.body,
                    priority=message.priority,
                )
            )
            message.mark_as_read()
        result = {"totalRecords": len(result), "messages": result}
        return result


class DeleteMessage(BrowserView):
    def __call__(self):
        self.context.delete()
