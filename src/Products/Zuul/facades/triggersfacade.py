##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import cgi
import logging
import parser
import zenoss.protocols.protobufs.zep_pb2 as zep

from copy import deepcopy
from zExceptions import BadRequest
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.interface import providedBy
from zope.schema import getFields
from zenoss.protocols.interfaces import IQueueSchema
from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.services.triggers import TriggerServiceClient
from AccessControl import getSecurityManager
from Acquisition import aq_parent
from Products.ZenModel.interfaces import IAction
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenModel.NotificationSubscriptionWindow import (
    NotificationSubscriptionWindow
)
from Products.ZenModel.Trigger import (
    Trigger,
    InvalidTriggerActionType,
    DuplicateTriggerName
)
from Products.ZenModel.UserSettings import GroupSettings
from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER,
    ZEN_MANAGER_ROLE,
)
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from Products.ZenUtils import Utils
from Products.Zuul import marshal
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IInfo
from Products.Zuul.decorators import require
from Products.Zuul.form.schema import Password

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):

    def __init__(self, context):
        super(TriggersFacade, self).__init__(context)

        self._guidManager = IGUIDManager(self._dmd)

        config = getGlobalConfiguration()
        schema = getUtility(IQueueSchema)
        self.triggers_service = TriggerServiceClient(
            config.get('zep_uri', 'http://localhost:8084'), schema
        )

        self.notificationPermissions = NotificationPermissionManager()
        self.triggerPermissions = TriggerPermissionManager()

    def _removeNode(self, obj):
        """
        Remove an object in ZODB.

        This method was created to provide a hook for unit tests.
        """
        context = aq_parent(obj)
        return context._delObject(obj.id)

    def _removeTriggerFromZep(self, uuid):
        """
        Remove a trigger from ZEP.

        This method was created to provide a hook for unit tests.
        """
        return self.triggers_service.removeTrigger(uuid)

    def removeNode(self, uid):
        obj = self._getObject(uid)
        return self._removeNode(obj)

    def _setTriggerGuid(self, trigger, guid):
        """
        @param trigger: The trigger object to set the guid on.
        @type trigger: Products.ZenModel.Trigger.Trigger
        @param guid: The guid
        @type guid: str

        This method was created to provide a hook for unit tests.
        """
        IGlobalIdentifier(trigger).guid = guid

    def _getTriggerGuid(self, trigger):
        """
        @param trigger: The trigger object in zodb.
        @type trigger: Products.ZenModel.Trigger.Trigger

        This method was created to provide a hook for unit tests.
        """
        return IGlobalIdentifier(trigger).guid

    def _setupTriggerPermissions(self, trigger):
        """
        This method was created to provide a hook for unit tests.
        """
        self.triggerPermissions.setupTrigger(trigger)

    def synchronize(self):
        """
        This method will first synchronize all triggers that exist in ZEP to
        their corresponding objects in ZODB. Then, it will clean up
        notifications and remove any subscriptions
        to triggers that no longer exist.
        """

        log.debug('SYNC: Starting trigger and notification synchronization.')

        _, trigger_set = self.triggers_service.getTriggers()

        zep_uuids = set(t.uuid for t in trigger_set.triggers)
        zodb_triggers = self._getTriggerManager().objectValues()

        # delete all triggers in zodb that do not exist in zep.
        for t in zodb_triggers:
            if not self._getTriggerGuid(t) in zep_uuids:
                log.info('SYNC: Found trigger in zodb that does not exist'
                         ' in zep, removing: %s', t.id)
                self._removeNode(t)

        zodb_triggers = self._getTriggerManager().objectValues()
        zodb_uuids = set(self._getTriggerGuid(t) for t in zodb_triggers)

        # create all triggers in zodb that do not exist in zep.
        for t in trigger_set.triggers:
            if t.uuid not in zodb_uuids and t.uuid.lower() not in zodb_uuids:
                log.info('SYNC: Found trigger uuid in zep that does not seem'
                         ' to exist in zodb, creating: %s', t.name)
                triggerObject = Trigger(str(t.name))
                try:
                    self._getTriggerManager()._setObject(
                        triggerObject.id, triggerObject
                    )
                except BadRequest:
                    # looks like the id already exists, remove this specific
                    # trigger from zep. This can happen if multiple
                    # createTrigger requests are sent from the browser at once
                    # the transaction will not abort until after the requests
                    # to create a trigger have already been sent to zep.
                    # See https://dev.zenoss.com/tracint/ticket/28272
                    log.info('SYNC: Found trigger with duplicate id in zodb,'
                             ' deleting from zep: %s (%s)',
                             triggerObject.id, t.uuid)
                    self._removeTriggerFromZep(t.uuid)
                else:
                    # setting a guid fires off events, we have to acquire the
                    # object before we adapt it, otherwise adapters responding
                    # to the event will get the 'regular' Trigger object and
                    # not be able to handle it.
                    self._setTriggerGuid(
                        self._getTriggerManager().findChild(triggerObject.id),
                        str(t.uuid)
                    )
                    self._setupTriggerPermissions(
                        self._getTriggerManager().findChild(t.name)
                    )

        # sync notifications
        for n in self._getNotificationManager().getChildNodes():
            is_changed = False

            subs = list(n.subscriptions)
            for s in subs:
                if s not in zep_uuids and s.lower() not in zep_uuids:
                    # this trigger no longer exists in zep, remove it from
                    # this notification's subscriptions.
                    log.info('SYNC: Notification subscription no longer'
                             ' valid: %s', s)
                    is_changed = True
                    n.subscriptions.remove(s)

            if is_changed:
                log.debug('SYNC: Updating notification subscriptions: %s',
                          n.id)
                self.updateNotificationSubscriptions(n)

        log.debug('SYNC: Trigger and notification synchronization complete.')

    def getTriggers(self):
        self.synchronize()

        user = getSecurityManager().getUser()
        response, trigger_set = self.triggers_service.getTriggers()
        trigger_set = to_dict(trigger_set)
        if 'triggers' in trigger_set:
            return self.triggerPermissions.findTriggers(
                user, self._guidManager, trigger_set['triggers']
            )
        else:
            return []

    def parseFilter(self, source):
        """
        Parse a filter to make sure it's sane.

        @param source: The python expression to test.
        @type source: string
        @todo: make this not allow nasty python.
        """
        if isinstance(source, basestring):
            if source:
                tree = parser.expr(source)
                if parser.isexpr(tree):
                    return source
                else:
                    raise Exception('Invalid filter expression.')
            else:
                return True  # source is empty string

    def addTrigger(self, newId):
        return self.createTrigger(
            name=newId,
            uuid=None,
            rule=dict(
                source=u'(dev.production_state == 1000) and (evt.severity >= 4)'
            )
        )

    @require(MANAGE_TRIGGER)
    def createTrigger(self, name, uuid=None, rule=None):
        # Fix for ZEN-28005 to thwart XSS attacks from incoming triggers
        name = cgi.escape(str(name))

        zodb_triggers = self._getTriggerManager().objectValues()
        zodb_trigger_names = set(t.id for t in zodb_triggers)
        if name in zodb_trigger_names:
            raise DuplicateTriggerName(
                'The id "%s" is invalid - it is already in use.' % name
            )

        triggerObject = Trigger(name)
        self._getTriggerManager()._setObject(name, triggerObject)
        acquired_trigger = self._getTriggerManager().findChild(name)

        if uuid:
            IGlobalIdentifier(acquired_trigger).guid = str(uuid)
        else:
            IGlobalIdentifier(acquired_trigger).create()

        self.triggerPermissions.setupTrigger(acquired_trigger)

        trigger = zep.EventTrigger()
        trigger.uuid = IGlobalIdentifier(acquired_trigger).guid
        trigger.name = name
        trigger.rule.api_version = 1
        trigger.rule.type = zep.RULE_TYPE_JYTHON
        if rule and 'source' in rule:
            trigger.rule.source = rule['source']
        else:
            trigger.rule.source = ''

        self.triggers_service.addTrigger(trigger)

        log.debug('Created trigger with uuid: %s', trigger.uuid)
        return trigger.uuid

    def removeTrigger(self, uuid):
        user = getSecurityManager().getUser()
        trigger = self._guidManager.getObject(uuid)

        if self.triggerPermissions.userCanUpdateTrigger(user, trigger):
            # If a user has the ability to update (remove) a trigger, it is
            # presumed that they will be consciously deleting triggers that
            # may have subscribers.
            #
            # Consider that that trigger may be subscribed to by notifications
            # that the current user cannot read/edit.

            # if there was an error,
            # the triggers service will throw an exception
            self._removeTriggerFromZep(uuid)

            context = aq_parent(trigger)
            context._delObject(trigger.id)

            relevant_notifications = self.getNotificationsBySubscription(uuid)

            updated_count = 0
            for n in relevant_notifications:
                n.subscriptions.remove(uuid)
                log.debug('Removing trigger uuid %s from notification: %s',
                          uuid, n.id)
                self.updateNotificationSubscriptions(n)
                updated_count += 1

            return updated_count
        else:
            log.warning('User not authorized to remove trigger: User: %s,'
                        ' Trigger: %s', user.getId(), trigger.id)
            raise Exception('User not authorized to remove trigger:'
                            ' User: %s, Trigger: %s', user.getId(), trigger.id)

    def getNotificationsBySubscription(self, trigger_uuid):
        for n in self._getNotificationManager().getChildNodes():
            if trigger_uuid in n.subscriptions:
                yield n

    def getTrigger(self, uuid):
        user = getSecurityManager().getUser()
        trigger = self._guidManager.getObject(uuid)
        if trigger is None:
            log.warning("Could not find trigger with uuid: %s", uuid)
            raise Exception("Could not find trigger with uuid: %s" % uuid)
        log.debug('Trying to fetch trigger: %s', trigger.id)
        if self.triggerPermissions.userCanViewTrigger(user, trigger):
            response, trigger = self.triggers_service.getTrigger(uuid)
            return to_dict(trigger)
        else:
            log.warning('User not authorized to view this trigger: %s',
                        trigger.id)
            raise Exception('User not authorized to view this trigger: %s',
                            trigger.id)

    def getTriggerList(self):
        """
        Retrieve a list of all triggers by uuid and name. This is used by the
        UI to render triggers that a user may not have permission to otherwise
        view, edit or manage.
        """
        response, trigger_set = self.triggers_service.getTriggers()
        trigger_set = to_dict(trigger_set)
        triggerList = []
        user = getSecurityManager().getUser()
        for t in trigger_set.get('triggers', []):
            trigger = self._guidManager.getObject(t['uuid'])
            if self.triggerPermissions.userCanViewTrigger(user, trigger):
                triggerList.append({
                    'uuid': t['uuid'],
                    'name': t['name']
                })
        return sorted(triggerList, key=lambda k: k['name'])

    def updateTrigger(self, **data):
        user = getSecurityManager().getUser()

        triggerObj = self._guidManager.getObject(data['uuid'])

        log.debug('Trying to update trigger: %s', triggerObj.id)

        if self.triggerPermissions.userCanManageTrigger(user, triggerObj):
            if 'globalRead' in data:
                triggerObj.globalRead = data.get('globalRead', False)
                log.debug('setting globalRead %s', triggerObj.globalRead)

            if 'globalWrite' in data:
                triggerObj.globalWrite = data.get('globalWrite', False)
                log.debug('setting globalWrite %s', triggerObj.globalWrite)

            if 'globalManage' in data:
                triggerObj.globalManage = data.get('globalManage', False)
                log.debug('setting globalManage %s', triggerObj.globalManage)

            triggerObj.users = data.get('users', [])
            self.triggerPermissions.clearPermissions(triggerObj)
            self.triggerPermissions.updatePermissions(
                self._guidManager, triggerObj
            )

        if self.triggerPermissions.userCanUpdateTrigger(user, triggerObj):
            if "name" in data:
                triggerObj.setTitle(cgi.escape(data["name"]))
                parent = triggerObj.getPrimaryParent()
                path = triggerObj.absolute_url_path()
                oldId = triggerObj.getId()
                newId = triggerObj.title
                if not isinstance(newId, unicode):
                    newId = Utils.prepId(newId)
                newId = newId.strip()
                if not newId:
                    raise Exception("New trigger id cannot be empty.")
                if newId != oldId:
                    # rename the trigger id since its title changed
                    try:
                        if triggerObj.getDmd().Triggers.findObject(newId):
                            message = 'Trigger %s already exists' % newId
                            # Duplicate trigger found
                            raise Exception(message)
                    except AttributeError as ex:
                        # the newId is not a duplicate
                        pass

                    try:
                        parent.manage_renameObject(oldId, newId)
                        triggerObj.id = newId
                    except CopyError:
                        raise Exception("Trigger rename failed.")

            trigger = from_dict(zep.EventTrigger, data)
            response, content = self.triggers_service.updateTrigger(trigger)
            return content

    def _getTriggerManager(self):
        return self._dmd.findChild('Triggers')

    def _getNotificationManager(self):
        return self._dmd.findChild('NotificationSubscriptions')

    def getNotifications(self):
        return self.getNotificationInfos()

    def getNotificationInfos(self):
        triggers = self.getTriggerList()

        def makeInfo(notification):
            notificationInfo = IInfo(notification)
            notificationInfo.subscriptions = [
                {"uuid": trigger["uuid"], "name": trigger["name"]}
                for trigger in triggers
                if trigger["uuid"] in notification.subscriptions
            ]
            return notificationInfo

        return (
            makeInfo(notification)
            for notification in self.getNotificationSubscriptions()
        )

    def getNotificationSubscriptions(self):
        self.synchronize()
        user = getSecurityManager().getUser()
        return (
            notification
            for notification in self._getNotificationManager().getChildNodes()
            if self.notificationPermissions.validate(user, notification)
        )

    def _updateContent(self, notification, data=None):

        try:
            util = getUtility(IAction, notification.action)
        except ComponentLookupError:
            raise InvalidTriggerActionType(
                "Invalid action type specified: %s" % notification.action
            )

        fields = {}
        for iface in providedBy(util.getInfo(notification)):
            f = getFields(iface)
            if f:
                fields.update(f)

        data = util.getDefaultData(self._dmd)
        for k, v in fields.iteritems():
            if k not in data:
                data[k] = v.default

        util.updateContent(notification.content, data)

    def addNotification(self, newId, action):
        notification = self.createNotification(newId, action)
        return IInfo(notification)

    @require(UPDATE_NOTIFICATION)
    def createNotification(self, id, action, guid=None):
        notification = NotificationSubscription(id)
        notification.action = action
        self._updateContent(notification)

        self._getNotificationManager()._setObject(id, notification)

        acquired_notification = self._getNotificationManager().findChild(id)
        self.notificationPermissions.setupNotification(acquired_notification)
        self.updateNotificationSubscriptions(notification)

        notification = self._getNotificationManager().findChild(id)
        notification.userRead = True
        notification.userWrite = True
        notification.userManage = True

        if guid:
            IGlobalIdentifier(notification).guid = guid

        return notification

    def removeNotification(self, uid):
        user = getSecurityManager().getUser()
        notification = self._getObject(uid)
        if self.notificationPermissions.userCanUpdateNotification(
            user, notification
        ):
            return self.removeNode(uid)
        else:
            log.warning('User not authorized to remove notification: User:'
                        ' %s, Notification: %s', user.getId(), notification.id)
            raise Exception('User not authorized to remove notification.')

    def getNotification(self, uid):
        user = getSecurityManager().getUser()
        notification = self._getObject(uid)
        if self.notificationPermissions.userCanViewNotification(
            user, notification
        ):
            log.debug('getting notification: %s', notification)
            return IInfo(notification)
        else:
            log.warning('User not authorized to view this notification: %s',
                        uid)
            raise Exception('User not authorized to view this notification:'
                            ' %s', uid)

    def updateNotificationSubscriptions(self, notification):
        triggerSubscriptions = []
        notification_guid = IGlobalIdentifier(notification).getGUID()
        for subscription in notification.subscriptions:
            triggerSubscriptions.append({
                'delay_seconds': notification.delay_seconds,
                'repeat_seconds': notification.repeat_seconds,
                'subscriber_uuid': notification_guid,
                'send_initial_occurrence':
                    notification.send_initial_occurrence,
                'trigger_uuid': subscription,
            })
        subscriptionSet = from_dict(
            zep.EventTriggerSubscriptionSet,
            {'subscriptions': triggerSubscriptions}
        )
        self.triggers_service.updateSubscriptions(
            notification_guid, subscriptionSet
        )

    def getPasswordFields(self, uid):
        notification = self._getObject(uid)
        action = getUtility(IAction, notification.action)
        passwordFields = set()

        for iface in providedBy(action.getInfo(notification)):
            f = getFields(iface)
            if f:
                for key, value in f.iteritems():
                    if isinstance(value, Password):
                        passwordFields.add(key)
        return passwordFields

    def updateNotification(self, **data):
        log.debug(data)

        uid = data['uid']

        # can't change action type after creation
        if 'action' in data:
            del data['action']

        note = self._getObject(uid)

        if not note:
            raise Exception('Could not find notification to update: %s' % uid)

        # don't update any properties unless the current user has the correct
        # permission.
        user = getSecurityManager().getUser()
        if self.notificationPermissions.userCanUpdateNotification(
            user, note
        ):
            # update the action content data
            action = getUtility(IAction, note.action)
            passwordFields = self.getPasswordFields(uid)

            for fieldName in passwordFields:
                if fieldName in data:
                    currValue = note.content.get(fieldName)
                    # match Products/Zuul/form/builder.py
                    maskedValue = '*' * len(currValue) if currValue else None
                    # if the value is all *, change to real password as it didn't change
                    if data[fieldName] == maskedValue:
                        data[fieldName] = currValue

            action.updateContent(note.content, data)

        if self.notificationPermissions.userCanManageNotification(
            user, note
        ):
            # if these values are not sent (in the case that the fields have
            # been disabled, do not set the value.
            if 'notification_globalRead' in data:
                note.globalRead = data.get('notification_globalRead')
                log.debug('setting globalRead')
            elif 'globalRead' in data:
                note.globalRead = data.get('globalRead')
                log.debug('setting globalRead')

            if 'notification_globalWrite' in data:
                note.globalWrite = data.get('notification_globalWrite')
                log.debug('setting globalWrite')
            elif 'globalWrite' in data:
                note.globalWrite = data.get('globalWrite')
                log.debug('setting globalWrite')

            if 'notification_globalManage' in data:
                note.globalManage = data.get(
                    'notification_globalManage'
                )
                log.debug('setting globalManage')
            elif 'globalManage' in data:
                note.globalManage = data.get('globalManage')
                log.debug('setting globalManage')

            for field in note._properties:
                note._updateProperty(
                    field['id'], data.get(field['id'])
                )

            note.subscriptions = data.get('subscriptions')
            self.updateNotificationSubscriptions(note)

            note.recipients = data.get('recipients', [])
            self.notificationPermissions.clearPermissions(note)
            self.notificationPermissions.updatePermissions(
                self._guidManager, note
            )

        log.debug('updated notification: %s', note)

    def getRecipientOptions(self):
        users = self._dmd.ZenUsers.getAllUserSettings()
        groups = self._dmd.ZenUsers.getAllGroupSettings()

        data = []

        for u in users:
            data.append(self.fetchRecipientOption(u))

        for g in groups:
            data.append(self.fetchRecipientOption(g))
        return data

    def fetchRecipientOption(self, recipient):
        my_type = 'group' if isinstance(recipient, GroupSettings) else 'user'
        return {
            'type': my_type,
            'label': '%s (%s)' % (recipient.getId(), my_type.capitalize()),
            'value': IGlobalIdentifier(recipient).getGUID(),
        }

    def getWindows(self, uid):
        notification = self._getObject(uid)
        for window in notification.windows():
            yield IInfo(window)

    def addWindow(self, contextUid, newId):
        notification = self._getObject(contextUid)
        window = NotificationSubscriptionWindow(newId)
        notification.windows._setObject(newId, window)
        new_window = notification.windows._getOb(newId)
        return IInfo(new_window)

    def removeWindow(self, uid):
        return self.removeNode(uid)

    def getWindow(self, uid):
        window = self._getObject(uid)
        return IInfo(window)

    def updateWindow(self, data):
        uid = data['uid']
        window = self._getObject(uid)

        if not window:
            raise Exception('Could not find window to update: %s' % uid)
        for field in window._properties:
            if field['id'] == 'start':
                # expect a unix timestamp
                setattr(window, 'start', int(data['start_ts']))
            elif field['id'] == 'duration':
                setattr(window, 'duration', int(data['duration']))
            else:
                setattr(window, field['id'], data.get(field['id']))

        log.debug('updated window')

    def exportConfiguration(self, triggerIds=None, notificationIds=None):
        notifications = []
        if notificationIds is None:
            notificationIds = []
            notifications = list(self.getNotifications())
        elif isinstance(notificationIds, str):
            notificationIds = [notificationIds]

        triggers = self.getTriggers()
        if triggerIds is not None:
            names = [triggerIds] if isinstance(triggerIds, str) else triggerIds
            triggers = [x for x in triggers if x['name'] in names]
            for trigger in triggers:
                uid = trigger['uuid']
                nsIds = [
                    x.id for x in self.getNotificationsBySubscription(uid)
                ]
                notificationIds.extend(nsIds)

        triggerData = self.exportTriggers(triggers)

        if notificationIds:
            notifications = [
                x for x in notifications if x.id in notificationIds
            ]

        notificationData = self.exportNotifications(notifications)

        return triggerData, notificationData

    def exportTriggers(self, triggers):
        configs = []
        junkColumns = ('id', 'newId')
        for config in triggers:
            for item in junkColumns:
                if item in config:
                    del config[item]
            configs.append(config)
        return configs

    def exportNotifications(self, notifications):
        configs = []
        junkColumns = ('id', 'newId', 'uid', 'inspector_type', 'meta_type')
        for notificationInfo in notifications:
            config = marshal(notificationInfo)
            for item in junkColumns:
                if item in config:
                    del config[item]

            contentsTab = self._extractNotificationContentInfo(config)
            del config['content']
            config.update(contentsTab)

            config['recipients'] = [r['label'] for r in config['recipients']]
            config['subscriptions'] = [
                x['name'] for x in config['subscriptions']
            ]

            windows = []
            for window in notificationInfo._object.windows():
                winconfig = marshal(IInfo(window))
                witems = ('meta_type', 'newId', 'id', 'inspector_type', 'uid')
                for witem in witems:
                    del winconfig[witem]
                windows.append(winconfig)
            config['windows'] = windows

            configs.append(config)
        return configs

    def _extractNotificationContentInfo(self, notification):
        contents = {}
        try:
            for itemInfo in notification['content']['items'][0]['items']:
                key = itemInfo['name']
                contents[key] = itemInfo['value']
        except Exception:
            log.exception("Unable to extract data from notifcation: %s",
                          notification)
        return contents

    def importConfiguration(self, triggers=None, notifications=None):
        itcount, incount = 0, 0
        if triggers:
            itcount = self.importTriggers(triggers)
        if notifications:
            incount = self.importNotifications(notifications)
        return itcount, incount

    def importTriggers(self, triggers):
        """
        Add any new trigger definitions to the system.

        Note: modifies the triggers argument
              to add 'new_uuid' to the definition.

        Does not attempt to link a trigger to a notification.
        """
        existingTriggers = [x['name'] for x in self.getTriggerList()]
        existingUsers = {
            "{} (User)".format(x.id): IGlobalIdentifier(x).getGUID()
            for x in self._dmd.ZenUsers.getAllUserSettings()
        }
        existingUsers.update({
            "{} (Group)".format(x.id): IGlobalIdentifier(x).getGUID()
            for x in self._dmd.ZenUsers.getAllGroupSettings()
        })

        removeDataList = ['subscriptions']

        imported = 0
        for trigger in triggers:
            name = trigger.get('name')
            if name is None:
                log.warn("Missing name in trigger definition: %s", trigger)
                continue
            if name in existingTriggers:
                log.warn("Skipping existing trigger '%s'", name)
                continue

            data = deepcopy(trigger)
            trigger['new_uuid'] = data['uuid'] = self.addTrigger(name)

            # Cleanup
            for key in removeDataList:
                if key in data:
                    del data[key]

            # Don't delete data from list you're looping through
            data['users'] = []
            for user in trigger.get('users', []):
                if user['label'] in existingUsers:
                    newuser = deepcopy(user)
                    newuser['value'] = existingUsers[user['label']]
                    data['users'].append(newuser)
                else:
                    log.warning("Unable to find trigger %s user '%s' on this"
                                " server -- skipping", name, user)

            # Make changes to the definition
            self.updateTrigger(**data)
            imported += 1

        return imported

    def importNotifications(self, notifications):
        """
        Add new notification definitions to the system.
        """
        existingNotifications = [x.id for x in self.getNotifications()]
        usersGroups = {x['label']: x for x in self.getRecipientOptions()}
        trigerToUuid = {x['name']: x['uuid'] for x in self.getTriggers()}

        imported = 0
        for notification in notifications:
            name = notification.get('name')
            if name is None:
                log.warn("Missing name in notification definition: %s",
                         notification)
                continue
            if name in existingNotifications:
                log.warn("Skipping existing notification '%s'", name)
                continue
            ntype = notification.get('action')
            if ntype is None:
                log.warn("Missing 'action' in notification definition: %s",
                         notification)
                continue

            data = deepcopy(notification)
            obj = self.createNotification(name, ntype)
            notification['uid'] = data['uid'] = obj.getPrimaryUrlPath()

            self.getRecipientsToImport(name, data, usersGroups)

            if 'action' in data:
                del data['action']

            self.linkImportedNotificationToTriggers(data, trigerToUuid)

            windows = data.get('windows', [])
            if windows:
                for window in windows:
                    iwindow = self.addWindow(data['uid'], window['name'])
                    del window['name']
                    window['uid'] = iwindow.uid
                    self.updateWindow(window)
                del data['windows']

            # Make changes to the definition
            self.updateNotification(**data)
            imported += 1

        return imported

    def getRecipientsToImport(self, name, data, usersGroups):
        recipients = []
        for recipient in data.get('recipients', []):
            label = recipient['label']
            if label in usersGroups:
                newrecipient = deepcopy(usersGroups[label])
                newrecipient['write'] = recipient.get('write', False)
                newrecipient['manage'] = recipient.get('manage', False)
                recipients.append(newrecipient)
            else:
                log.warn('Unable to find %s for recipients for notification'
                         ' %s', label, name)
        data['recipients'] = recipients

    def linkImportedNotificationToTriggers(self, notification, trigerToUuid):
        subscriptions = []
        for subscription in notification.get('subscriptions', []):
            uuid = trigerToUuid.get(subscription)
            if uuid is not None:
                subscriptions.append(uuid)
            else:
                log.warn("Unable to link notification %s to missing trigger"
                         " '%s'", notification['name'], subscription['name'])
        notification['subscriptions'] = subscriptions


class TriggerPermissionManager(object):
    """
    This object helps manage permissions with regard to a trigger. Triggers are
    only stored in the zodb for managing permissions, all of the data
    associated with a trigger is stored externally in ZEP.
    """

    def __init__(self):
        self.securityManager = getSecurityManager()

    def userCanViewTrigger(self, user, trigger):
        return trigger.globalRead or \
            self.securityManager.checkPermission(VIEW_TRIGGER, trigger)

    def userCanUpdateTrigger(self, user, trigger):
        return trigger.globalWrite or \
            self.securityManager.checkPermission(UPDATE_TRIGGER, trigger)

    def userCanManageTrigger(self, user, trigger):
        return trigger.globalManage or \
            self.securityManager.checkPermission(MANAGE_TRIGGER, trigger)

    def findTriggers(self, user, guidManager, triggers):
        results = []
        for trigger in triggers:
            triggerObject = guidManager.getObject(trigger['uuid'])
            if triggerObject and self.userCanViewTrigger(user, triggerObject):

                # copy these properties that are stored on the dmd object to
                # the json-friendly object that is getting passed to the UI
                trigger['globalRead'] = triggerObject.globalRead
                trigger['globalWrite'] = triggerObject.globalWrite
                trigger['globalManage'] = triggerObject.globalManage

                trigger['userRead'] = True
                trigger['userWrite'] = self.userCanUpdateTrigger(
                    user, triggerObject
                )
                trigger['userManage'] = self.userCanManageTrigger(
                    user, triggerObject
                )

                trigger['users'] = triggerObject.users

                results.append(trigger)

        return results

    def clearPermissions(self, trigger):
        # remove all previous local roles, besides 'Owner'
        removeUserIds = []
        for userId, roles in trigger.get_local_roles():
            if OWNER_ROLE not in roles:
                removeUserIds.append(userId)
        log.debug('Removing all local roles for users: %s', removeUserIds)
        trigger.manage_delLocalRoles(removeUserIds)

    def updatePermissions(self, guidManager, trigger):
        # then add local roles back for all the users/groups that we just added
        for user_info in trigger.users:
            log.debug(user_info)
            if user_info['type'] != 'manual':
                userOrGroup = guidManager.getObject(user_info['value'])

                trigger.manage_addLocalRoles(
                    userOrGroup.id, [TRIGGER_VIEW_ROLE]
                )
                log.debug('Added role: %s for user or group: %s',
                          TRIGGER_VIEW_ROLE, userOrGroup.id)

                if user_info.get('write'):
                    trigger.manage_addLocalRoles(
                        userOrGroup.id, [TRIGGER_UPDATE_ROLE]
                    )
                    log.debug('Added role: %s for user or group: %s',
                              TRIGGER_UPDATE_ROLE, userOrGroup.id)

                if user_info.get('manage'):
                    trigger.manage_addLocalRoles(
                        userOrGroup.id, [TRIGGER_MANAGER_ROLE]
                    )
                    log.debug('Added role: %s for user or group: %s',
                              TRIGGER_MANAGER_ROLE, userOrGroup.id)

    def setupTrigger(self, trigger):
        # Permissions are managed here because managing these default
        # permissions on the class was not preventing the permissions
        # from being acquired elsewhere.
        trigger.manage_permission(
            VIEW_TRIGGER,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             TRIGGER_VIEW_ROLE,
             TRIGGER_UPDATE_ROLE,
             TRIGGER_MANAGER_ROLE),
            acquire=False
        )

        trigger.manage_permission(
            UPDATE_TRIGGER,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             TRIGGER_UPDATE_ROLE),
            acquire=False
        )

        trigger.manage_permission(
            MANAGE_TRIGGER,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             TRIGGER_MANAGER_ROLE),
            acquire=False
        )


class NotificationPermissionManager(object):
    """
    This object helps manage permissions with regard to a notification.
    """

    def __init__(self):
        self.securityManager = getSecurityManager()

    def userCanViewNotification(self, user, notification):
        """
        Check to see if the current user can view this notification. Take into
        account global settings of the notification, and then just defer a
        permission check to zope.
        """
        return notification.globalRead or \
            self.securityManager.checkPermission(
                VIEW_NOTIFICATION, notification
            )

    def userCanUpdateNotification(self, user, notification):
        """
        check to see if the current user can update the notification. Take into
        account global settings of the notification, and then just defer a
        permission check to zope.
        """
        return notification.globalWrite or \
            self.securityManager.checkPermission(
                UPDATE_NOTIFICATION, notification
            )

    def userCanManageNotification(self, user, notification):
        return notification.globalManage or \
            self.securityManager.checkPermission(
                MANAGE_NOTIFICATION_SUBSCRIPTIONS, notification
            )

    def validate(self, user, notification):
        """Checks whether the given user may read the notification, and if
        so, updates the notification's userWrite and userManage statuses
        to reflect the user's permission level on those privileges.

        Returns True if the user may read the notification.
        """
        if not self.userCanViewNotification(user, notification):
            return False

        notification.userRead = True
        notification.userWrite = \
            self.userCanUpdateNotification(user, notification)
        notification.userManage = \
            self.userCanManageNotification(user, notification)
        return True

    def findNotifications(self, user, notifications):
        """
        Find all notifications that the current user at least has the 'View'
        permission on.
        """
        for notification in notifications:
            if self.validate(user, notification):
                yield notification

    def clearPermissions(self, notification):
        # remove all previous local roles, besides 'Owner'
        removeUserIds = []
        for userId, roles in notification.get_local_roles():
            if OWNER_ROLE not in roles:
                removeUserIds.append(userId)
        log.debug('Removing all local roles for users: %s', removeUserIds)
        notification.manage_delLocalRoles(removeUserIds)

    def updatePermissions(self, guidManager, notification):
        # then add local roles back for all the users/groups that we just added
        recipientsForRemoval = {}
        for recipient in notification.recipients:
            if recipient['type'] != 'manual':
                userOrGroup = guidManager.getObject(recipient['value'])
                if not userOrGroup:
                    recipientsForRemoval[recipient['value']] = recipient
                    log.info(
                        'Recipient %s not found: it may have been deleted.'
                        ' This recipient will be removed from the notification'
                        ' %s.', recipient['label'], notification.id
                    )
                    continue

                notification.manage_addLocalRoles(
                    userOrGroup.id, [NOTIFICATION_VIEW_ROLE]
                )
                log.debug('Added role: %s for user or group: %s',
                          NOTIFICATION_VIEW_ROLE, userOrGroup.id)
                log.debug(recipient)

                if recipient.get('write'):
                    notification.manage_addLocalRoles(
                        userOrGroup.id, [NOTIFICATION_UPDATE_ROLE]
                    )
                    log.debug('Added role: %s for user or group: %s',
                              NOTIFICATION_UPDATE_ROLE, userOrGroup.id)

                if recipient.get('manage'):
                    notification.manage_addLocalRoles(
                        userOrGroup.id,
                        [NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE]
                    )
                    log.debug(
                        'Added role: %s for user or group: %s',
                        NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE,
                        userOrGroup.id
                    )

        notification.recipients = [
            recip for recip in notification.recipients
            if recip['value'] not in recipientsForRemoval
        ]

    def setupNotification(self, notification):
        # Permissions are managed here because managing these default
        # permissions on the class was not preventing the permissions from
        # being acquired elsewhere.
        notification.manage_permission(
            VIEW_NOTIFICATION,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             NOTIFICATION_VIEW_ROLE,
             NOTIFICATION_UPDATE_ROLE,
             NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE),
            acquire=False
        )

        notification.manage_permission(
            UPDATE_NOTIFICATION,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             NOTIFICATION_UPDATE_ROLE),
            acquire=False
        )

        notification.manage_permission(
            MANAGE_NOTIFICATION_SUBSCRIPTIONS,
            (OWNER_ROLE,
             MANAGER_ROLE,
             ZEN_MANAGER_ROLE,
             NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE),
            acquire=False
        )
