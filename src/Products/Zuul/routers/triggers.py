##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from operator import itemgetter
from Products import Zuul
from zope.component import getUtilitiesFor
from Products.ZenModel.interfaces import IAction
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import serviceConnectionError
from zenoss.protocols.protobufs.zep_pb2 import RULE_TYPE_JYTHON
from Products.ZenMessaging.audit import audit
from Products.ZenModel.Trigger import DuplicateTriggerName

import logging

log = logging.getLogger('zen.triggers')


class TriggersRouter(DirectRouter):
    """
    Router for Triggers UI section under Events.
    """

    def _getFacade(self):
        return Zuul.getFacade('triggers', self)

    @serviceConnectionError
    def getTriggers(self, **kwargs):
        return DirectResponse.succeed(data=self._getFacade().getTriggers())

    @serviceConnectionError
    def getTriggerList(self, **unused):
        return DirectResponse.succeed(data=self._getFacade().getTriggerList())

    @serviceConnectionError
    def addTrigger(self, newId):
        try:
            data = self._getFacade().addTrigger(newId)
        except DuplicateTriggerName as tnc:
            log.debug("Exception DuplicateTriggerName: %s", tnc)
            return DirectResponse.fail(str(tnc))
        else:
            audit('UI.Trigger.Add', newId)
            return DirectResponse.succeed(data=data)

    @serviceConnectionError
    def removeTrigger(self, uuid):
        trigger = self._getFacade().getTrigger(uuid)
        updated_count = self._getFacade().removeTrigger(uuid)
        audit('UI.Trigger.Remove', trigger['name'])
        msg = "Trigger removed successfully. {count} {noun} {verb} updated.".format(
            count=updated_count,
            noun='notification' if updated_count == 1 else 'notifications',
            verb='was' if updated_count == 1 else 'were'
        )
        return DirectResponse.succeed(msg=msg, data=None)

    @serviceConnectionError
    def getTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().getTrigger(uuid))

    @serviceConnectionError
    def updateTrigger(self, **data):
        data['rule']['api_version'] = 1
        data['rule']['type'] = RULE_TYPE_JYTHON
        triggerUid = data['uuid']
        try:
            response = self._getFacade().updateTrigger(**data)
        except Exception:
            return DirectResponse.fail(msg='Trigger not updated')
        audit('UI.Trigger.Edit', triggerUid, data_=data)
        return DirectResponse.succeed(
            msg="Trigger updated successfully.", data=response
        )

    @serviceConnectionError
    def parseFilter(self, source):
        try:
            response = self._getFacade().parseFilter(source)
            return DirectResponse.succeed(data=response)
        except Exception as err:
            log.exception()
            return DirectResponse.exception(
                err,
                'Error parsing filter source. Please check your syntax.'
            )

    # notification subscriptions
    @serviceConnectionError
    def getNotifications(self):
        response = self._getFacade().getNotificationInfos()
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addNotification(self, newId, action):
        response = self._getFacade().addNotification(newId, action)
        audit('UI.Notification.Add', newId)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeNotification(self, uid):
        response = self._getFacade().removeNotification(uid)
        audit('UI.Notification.Remove', uid)
        return DirectResponse.succeed(
            msg="Notification removed successfully.", data=response
        )

    @serviceConnectionError
    def getNotificationTypes(self, query=''):
        utils = getUtilitiesFor(IAction)
        actionTypes = sorted(
            (dict(id=id, name=util.name) for id, util in utils),
            key=itemgetter('id')
        )
        log.debug('notification action types are: %s', actionTypes)
        return DirectResponse.succeed(data=actionTypes)

    @serviceConnectionError
    def getNotification(self, uid):
        response = self._getFacade().getNotification(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateNotification(self, **data):
        notificationUid = data['uid']
        facade = self._getFacade()
        passwordFields = facade.getPasswordFields(notificationUid)
        try:
            response = facade.updateNotification(**data)
        except Exception:
            return DirectResponse.fail(msg='Notification not updated')
        audit('UI.Notification.Edit', object_=notificationUid,
            data_=data, maskFields_=passwordFields)
        return DirectResponse.succeed(
            msg="Notification updated successfully.",
            data=Zuul.marshal(response)
        )

    @serviceConnectionError
    def getRecipientOptions(self, **kwargs):
        data = self._getFacade().getRecipientOptions()
        return DirectResponse.succeed(data=data)

    # subscription windows
    @serviceConnectionError
    def getWindows(self, uid, **kwargs):
        response = self._getFacade().getWindows(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addWindow(self, contextUid, newId):
        response = self._getFacade().addWindow(contextUid, newId)
        audit('UI.NotificationWindow.Add', newId, notification=contextUid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeWindow(self, uid):
        response = self._getFacade().removeWindow(uid)
        audit('UI.NotificationWindow.Remove', uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def getWindow(self, uid):
        response = self._getFacade().getWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateWindow(self, **data):
        windowUid = data['uid']
        response = self._getFacade().updateWindow(data)
        audit('UI.NotificationWindow.Edit', windowUid, data_=data)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def exportConfiguration(self, triggerIds=None, notificationIds=None):
        facade = self._getFacade()
        triggers, notifications = facade.exportConfiguration(
            triggerIds, notificationIds
        )
        msg = "Exported %d triggers and %d notifications" % (
            len(triggers), len(notifications)
        )
        audit('UI.TriggerNotification.Export', msg)
        return DirectResponse.succeed(
            triggers=Zuul.marshal(triggers),
            notifications=Zuul.marshal(notifications),
            msg=msg
        )

    @serviceConnectionError
    def importConfiguration(self, triggers=None, notifications=None):
        try:
            tcount = len(triggers) if triggers is not None else 0
            ncount = len(notifications) if notifications is not None else 0
            facade = self._getFacade()
            itcount, incount = facade.importConfiguration(
                triggers, notifications
            )
            msg = "Imported %d of %d triggers and %d of %d notifications" % (
                tcount, itcount, ncount, incount
            )
            audit('UI.TriggerNotification.Import', msg)
            return DirectResponse.succeed(msg=msg)
        except Exception as ex:
            audit('UI.TriggerNotification.Import',
                  "Failed to import trigger/notification data")
            log.exception(
                "Unable to import data:\ntriggers=%r\nnotifications=%r",
                triggers, notifications
            )
            return DirectResponse.fail(str(ex))
