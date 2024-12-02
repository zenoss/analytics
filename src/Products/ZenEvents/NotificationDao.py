##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################



from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.guid.guid import GUIDManager

from Products.ZenModel.NotificationSubscription import NotificationSubscriptionManager

import logging
log = logging.getLogger("zen.notificationdao")


class NotificationDao(object):
    def __init__(self, dmd):
        self.dmd = dmd
        self.notification_manager = self.dmd.getDmdRoot(NotificationSubscriptionManager.root)
        self.guidManager = GUIDManager(dmd)

    def getNotifications(self):
        self.dmd._p_jar.sync()
        return self.notification_manager.getChildNodes()

    def getSignalNotifications(self, signal):
        """
        Given a signal, find which notifications match this signal. In order to
        match, a notification must be active (enabled and if has maintenance
        windows, at least one must be active) and must be subscribed to the
        signal.

        @param signal: The signal for which to get subscribers.
        @type signal: protobuf zep.Signal
        """
        active_matching_notifications = []
        for notification in self.getNotifications():
            if notification.isActive():
                if self.notificationSubscribesToSignal(notification, signal):
                    active_matching_notifications.append(notification)
                    log.debug('Found matching notification: %s', notification)
                else:
                    log.debug('Notification "%s" does not subscribe to this signal.', notification)
            else:
                log.debug('Notification "%s" is not active.', notification)

        return active_matching_notifications

    def notificationSubscribesToSignal(self, notification, signal):
        """
        Determine if the notification matches the specified signal.

        @param notification: The notification to check
        @type notification: NotificationSubscription
        @param signal: The signal to match.
        @type signal: zenoss.protocols.protbufs.zep_pb2.Signal

        @rtype boolean
        """
        return signal.subscriber_uuid == IGlobalIdentifier(notification).getGUID()

