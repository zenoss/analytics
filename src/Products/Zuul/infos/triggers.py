##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
log = logging.getLogger('zen.triggerinfos')

from datetime import datetime
from time import time
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements
from zope.component import getUtility
from Products.ZenModel.interfaces import IAction
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.interfaces import (
    INotificationWindowInfo,
    INotificationSubscriptionInfo
)


def generateMissingJavascript():
    return {
        'items': [{
            'xtype': 'panel',
            'html': 'This action type is missing. Please re-install this type '
                    'or migrate this notification to another type.'
        }]
    }


class NotificationSubscriptionInfo(InfoBase):
    implements(INotificationSubscriptionInfo)

    @property
    def newId(self):
        return self._object.id

    enabled = ProxyProperty('enabled')
    send_clear = ProxyProperty('send_clear')
    send_initial_occurrence = ProxyProperty('send_initial_occurrence')

    delay_seconds = ProxyProperty('delay_seconds')
    repeat_seconds = ProxyProperty('repeat_seconds')

    def _getAction(self):
        try:
            if getUtility(IAction, self._object.action):
                return self._object.action
        except ComponentLookupError:
            # Zenpack may have been removed
            return '%s (MISSING)' % self._object.action

    def _setAction(self, value):
        pass

    action = property(_getAction, _setAction)

    recipients = ProxyProperty('recipients')

    globalRead = ProxyProperty('globalRead')
    globalWrite = ProxyProperty('globalWrite')
    globalManage = ProxyProperty('globalManage')

    userRead = ProxyProperty('userRead')
    userWrite = ProxyProperty('userWrite')
    userManage = ProxyProperty('userManage')

    def _getContent(self):
        try:
            util = getUtility(IAction, self._object.action)
            return util.generateJavascriptContent(self._object)
        except ComponentLookupError:
            # Zenpack may have been removed, best I can do is default to email.
            return generateMissingJavascript()

    def _setContent(self, value):
        self._object.content = value

    content = property(_getContent, _setContent)

    subscriptions = []


class NotificationWindowInfo(InfoBase):
    implements(INotificationWindowInfo)

    @property
    def newId(self):
        return self._object.id

    @property
    def start_ts(self):
        return self._object.start

    def _getStart(self):
        # is a unix timestamp convert to string
        start = time()
        try:
            start = float(self._object.start)
        except (ValueError, TypeError):
            pass
        dt = datetime.utcfromtimestamp(start)
        # we want the format in mm/dd/yyyy
        return "%.2d/%.2d/%d" % (dt.month, dt.day, dt.year)

    def _setStart(self, value):
        # convert string to unix time stamp
        # expecting the time to always be in the following format
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        self._object.start = dt.strftime('%s')

    def _getStartTime(self):
        starttime = time()
        try:
            starttime = float(self._object.start)
        except (ValueError, TypeError):
            pass
        dt = datetime.fromtimestamp(starttime)
        return '%.2d:%.2d' % (dt.hour, dt.minute)

    def _setStartTime(self, value):
        pass

    start = property(_getStart, _setStart)
    starttime = property(_getStartTime, _setStartTime)
    enabled = ProxyProperty('enabled')
    repeat = ProxyProperty('repeat')
    duration = ProxyProperty('duration')
