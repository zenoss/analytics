##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
from zExceptions import BadRequest

log = logging.getLogger('zen.test_triggersFacade')

import unittest
from Products.Zuul.facades.triggersfacade import TriggersFacade
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenModel.Trigger import Trigger
from zenoss.protocols.jsonformat import from_dict

from zenoss.protocols.protobufs import zep_pb2 as zep

from uuid import uuid4


def _triggerFactory(guid, id):
    data = dict(
        uuid = guid,
        name = id,
        rule = dict(
            api_version = 1,
            type = 1,
            source = ''
        ),
        subscriptions = []
    )
    return data

mock_zodb_trigger_a = Trigger('mock_trigger_a')
mock_zodb_trigger_a._mock_guid = str(uuid4())
mock_zep_trigger_a = _triggerFactory(
    mock_zodb_trigger_a._mock_guid,
    mock_zodb_trigger_a.id
)

mock_zodb_trigger_b = Trigger('mock_trigger_b')
mock_zodb_trigger_b._mock_guid = str(uuid4())
mock_zep_trigger_b = _triggerFactory(
    mock_zodb_trigger_b._mock_guid,
    mock_zodb_trigger_b.id
)

mock_zodb_trigger_c = Trigger('mock_trigger_c')
mock_zodb_trigger_c._mock_guid = str(uuid4())
mock_zep_trigger_c = _triggerFactory(
    mock_zodb_trigger_c._mock_guid,
    mock_zodb_trigger_c.id
)

# duplicate id as mock_zodb_trigger_c
mock_zep_trigger_d = _triggerFactory(
    str(uuid4()),
    mock_zodb_trigger_c.id
)

# duplicate id as mock_zodb_trigger_c
mock_zep_trigger_e = _triggerFactory(
    str(uuid4()),
    mock_zodb_trigger_c.id
)

# This notification starts subscribed to all three triggers and will
# be used in testing the syncronization of removing a trigger and
# having notifications update and remove invalid subscriptions.
mock_notification_a = NotificationSubscription('mock_a')
mock_notification_a.subscriptions = [
        mock_zodb_trigger_a._mock_guid,
        mock_zodb_trigger_b._mock_guid,
        mock_zodb_trigger_c._mock_guid,
]
mock_notification_b = NotificationSubscription('mock_b')
mock_notification_b.subscriptions = [
        mock_zodb_trigger_a._mock_guid,
]
mock_notification_c = NotificationSubscription('mock_c')
mock_notification_c.subscriptions = []


class MockNotificationManager(object):
    """
    This mock object emulates the storage of notifications in zodb.
    """

    def __init__(self):
        self.notifications = dict()
        self.notifications[mock_notification_a.id] = mock_notification_a
        self.notifications[mock_notification_b.id] = mock_notification_b
        self.notifications[mock_notification_c.id] = mock_notification_c

    def getChildNodes(self):
        return self.notifications.values()

    
class MockTriggerManager(object):
    """
    This mock object emulates the storage of the stub trigger objects used for
    permissions in zodb.
    """
    def __init__(self):
        self.triggers = dict()
        self.triggers[mock_zodb_trigger_a.id] = mock_zodb_trigger_a
        self.triggers[mock_zodb_trigger_b.id] = mock_zodb_trigger_b
        self.triggers[mock_zodb_trigger_c.id] = mock_zodb_trigger_c

    def objectValues(self):
        return self.triggers.values()

    def _setObject(self, id, trigger):
        if id in self.triggers:
            raise BadRequest('Duplicate id.')
        self.triggers[id] = trigger

    def findChild(self, id):
        return self.triggers[id]


class MockTriggersService(object):
    def __init__(self):
        self.triggers = {
            mock_zep_trigger_a['uuid'] : mock_zep_trigger_a,
            mock_zep_trigger_b['uuid'] : mock_zep_trigger_b,
            mock_zep_trigger_c['uuid'] : mock_zep_trigger_c
        }

    def getTriggers(self):
        trigger_set_data = {'triggers':self.triggers.values()}
        trigger_set = from_dict(zep.EventTriggerSet, trigger_set_data)
        return None, trigger_set


class MockTriggersFacade(TriggersFacade):
    def __init__(self, trigger_service, trigger_manager, notification_manager):
        self.triggers_service = trigger_service
        self._trigger_manager = trigger_manager
        self._notification_manager = notification_manager

    def _removeTriggerFromZep(self, uuid):
        if uuid in self.triggers_service.triggers:
            del self.triggers_service.triggers[uuid]

    def _removeNode(self, obj):
        if isinstance(obj, Trigger):
            del self._trigger_manager.triggers[obj.id]
        elif isinstance(obj, NotificationSubscription):
            del self._notification_manager.notifications[obj.id]

    def _getTriggerGuid(self, trigger):
        return trigger._mock_guid

    def _setTriggerGuid(self, trigger, guid):
        trigger._mock_guid = guid

    def _getTriggerManager(self):
        return self._trigger_manager

    def _getNotificationManager(self):
        return self._notification_manager

    def _setupTriggerPermissions(self, trigger):
        pass

    def updateNotificationSubscriptions(self, notification):
        """
        This method updates the subscriptions in zep; these are the things that
        drive the trigger spool and fire signals. These tests do not cover that
        functionality.
        """
        pass

class TriggersFacadeTest(BaseTestCase):
    def afterSetUp(self):
        super(TriggersFacadeTest, self).afterSetUp()

        self.trigger_service = MockTriggersService()
        self.trigger_manager = MockTriggerManager()
        self.notification_manager = MockNotificationManager()
        self.facade = MockTriggersFacade(
            self.trigger_service,
            self.trigger_manager,
            self.notification_manager
        )

    def _are_in_sync(self):
        _, trigger_set = self.trigger_service.getTriggers()
        zep_triggers = trigger_set.triggers
        zodb_triggers = self.trigger_manager.objectValues()

        zodb_uuids = [self.facade._getTriggerGuid(t) for t in zodb_triggers]
        for t in zep_triggers:
            if not t.uuid in zodb_uuids:
                log.debug('Uuid %s not found in zodb uuids.' % t.uuid)
                return False

        zep_uuids = [t.uuid for t in zep_triggers]
        for t in zodb_triggers:
            if not self.facade._getTriggerGuid(t) in zep_uuids:
                log.debug('Uuid %s not found in zep uuids.' % self.facade._getTriggerGuid(t))
                return False

        return True
    
    def _subscriptions_are_valid(self):
        _, trigger_set = self.trigger_service.getTriggers()
        zep_triggers = trigger_set.triggers
        notifications = self.notification_manager.getChildNodes()
        zep_uuids = [t.uuid for t in zep_triggers]
        for n in notifications:
            for s in n.subscriptions:
                if not s in zep_uuids:
                    log.debug('Notification subscription not found in zep triggers.')
                    return False
        return True

    def _check(self):
        self.facade.synchronize()

        # Verify that mock data is still in sync after a synchronize call.
        self.assertTrue(self._are_in_sync(), 'ZEP/ZODB triggers not in sync.')

        # Verify that mock notification subscriptions are in sync.
        self.assertTrue(self._subscriptions_are_valid(), 'Notification subscriptions not in sync.')

    def testSynchronize(self):

        # Verify that mock data is in sync.
        self.assertTrue(self._are_in_sync(), 'ZEP/ZODB triggers not in sync.')

        # Verify that with a matching set of data, facade.synchronize performs
        # as expected and does nothing to the data.
        self._check()


    def testSynchronizeToZodb(self):

        # Simulate a bad state by manually removing a zodb trigger.
        del self.trigger_manager.triggers[mock_zodb_trigger_c.id]

        # Verify that zodb is out of sync.
        self.assertFalse(self._are_in_sync(),
            'ZEP/ZODB triggers are in sync when they should not be.')

        # Synchronize and verify that things corrected themselves.
        self._check()

    
    def testSynchronizeFromZep(self):

        # Simulate a bad state by manually removing a zep trigger.
        self.facade._removeTriggerFromZep(mock_zep_trigger_c['uuid'])

        # Verify that zodb is out of sync after deleting zep trigger.
        self.assertFalse(self._are_in_sync(),
            'ZEP/ZODB triggers are in sync when they should not be.')

        # Synchronize and verify that things corrected themselves.
        self._check()


    def testSynchronizeExtrasFromZep(self):
        
        # simulate a bad state by manually adding some duplicates to zep
        self.trigger_service.triggers[mock_zep_trigger_d['uuid']] = mock_zep_trigger_d
        self.trigger_service.triggers[mock_zep_trigger_e['uuid']] = mock_zep_trigger_e
        
        # Verify that zodb is out of sync after deleting zep trigger.
        self.assertFalse(self._are_in_sync(),
            'ZEP/ZODB triggers are in sync when they should not be.')

        # Synchronize and verify that things corrected themselves.
        self._check()

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TriggersFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
