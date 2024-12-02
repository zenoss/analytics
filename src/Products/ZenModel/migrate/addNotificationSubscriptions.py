##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenModel.NotificationSubscription import NotificationSubscriptionManager, \
    manage_addNotificationSubscriptionManager
from Products.Zuul.utils import safe_hasattr as hasattr

class NotificationSubscriptions(Migrate.Step):
    version = Migrate.Version(4,0,0)
    
    def cutover(self, dmd):
        if not hasattr(dmd, NotificationSubscriptionManager.root):
            manage_addNotificationSubscriptionManager(dmd)

notificationSubscriptions = NotificationSubscriptions()
