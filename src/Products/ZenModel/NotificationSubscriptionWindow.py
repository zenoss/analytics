##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging

log = logging.getLogger("zen.notificationwindows")

import time
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow

class NotificationSubscriptionWindow(MaintenanceWindow):

    notificationSubscription = None

    backCrumb = "triggers"

    _relations = MaintenanceWindow._relations + (
        ("notificationSubscription",
        ToOne(
            ToManyCont,
            "Products.ZenModel.NotificationSubscription",
            "windows"
        )),
    )

    _properties = tuple(list(MaintenanceWindow._properties) + [
        {'id':'enabled', 'type':'boolean', 'mode':'w'}
    ])

    def target(self):
        return self.notificationSubscription()

    def begin(self, now=None, batchSize=None, inTransaction=False):
        if self.started is not None:
            log.debug('Notification Subscription Window is trying to begin after'
                ' it is already started: Start: %s, Duration: %s',
                self.started, self.duration)

        self.target().enabled = True
        if not now:
            now = time.time()
        self.started = now

    def end(self, batchSize=None, inTransaction=False):
        self.started = None
        self.target().enabled = False
