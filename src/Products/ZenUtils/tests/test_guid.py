##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


'''
Note that this is meant to be run from zopecctl using the "test" option. If you
would like to run these tests from python, simply to the following:

    python ZenUtils/Version.py
'''
import unittest
from zope.interface import implements
from Zope2.App import zcml

from OFS.SimpleItem import SimpleItem
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.component import provideHandler

from ..guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier
from ..guid.interfaces import IGUIDEvent, IGUIDManager

from ..guid.guid import GlobalIdentifier


class Identifiable(SimpleItem):
    implements(IGloballyIdentifiable)
    def __init__(self, id, parent):
        self.id = id
        self.parent = parent
    def unrestrictedTraverse(self, path):
        return self.parent.unrestrictedTraverse(path)
    def getPrimaryUrlPath(self):
        return self.absolute_url_path()


class TestGuid(BaseTestCase):

    def afterSetUp(self):
        super(TestGuid, self).afterSetUp()

        self.ob = Identifiable('identifiable', self.dmd)
        self.dmd._setOb(self.ob.id, self.ob)
        self.aq_ob = self.dmd.identifiable
        zcml.load_string("""
        <configure xmlns="http://namespaces.zope.org/zope">
            <adapter
                for="Products.ZenUtils.guid.interfaces.IGloballyIdentifiable"
                provides="Products.ZenUtils.guid.interfaces.IGlobalIdentifier"
                factory="Products.ZenUtils.guid.guid.GlobalIdentifier"
                />
            <adapter
                for="Products.ZenUtils.tests.test_guid.Identifiable"
                provides="Products.ZenUtils.guid.interfaces.IGUIDManager"
                factory="Products.ZenUtils.guid.guid.GUIDManager"
                />
            <include package="Products.Five" file="event.zcml" />
            <subscriber handler="Products.ZenUtils.guid.event.registerGUIDToPathMapping"/>
            <subscriber handler="Products.ZenUtils.guid.event.refireEventOnObjectAddOrMove"/>
            <subscriber handler="Products.ZenUtils.guid.event.refireEventOnObjectBeforeRemove"/>
        </configure>
        """)

    def test_identifier(self):
        identifier = IGlobalIdentifier(self.ob)
        self.assert_(isinstance(identifier, GlobalIdentifier))

        # Don't have a guid yet
        self.assertEqual(identifier.guid, None)

        # Create one and make sure it is set
        guid = identifier.create()
        self.assertEqual(identifier.guid, guid)

        # Create again and see that it didn't change
        newguid = identifier.create()
        self.assertEqual(identifier.guid, newguid, guid)

        # Create with force and see that it did change
        newerguid = identifier.create(force=True)
        self.assertNotEqual(identifier.guid, newguid)

        # Set it manually and see that it is set
        identifier.guid = newguid
        self.assertEqual(newguid, identifier.guid)

        # Make a new identifier and see that it persists
        self.assertEqual(IGlobalIdentifier(self.ob).guid, newguid)

    def skip_this_test__table_creation(self):
        # Make sure it isn't there first
        self.assertEqual(getattr(self.dmd, 'guid_table', None), None)
        # Make a manager
        mgr = IGUIDManager(self.aq_ob)
        # See that the table was created
        self.assertNotEqual(getattr(self.dmd, 'guid_table', None), None)
        self.assertEqual(self.dmd.guid_table, mgr.table)

    def test_guid_event_is_fired(self):
        events = []
        provideHandler(lambda *x:events.append(x), (IGloballyIdentifiable,
                                                    IGUIDEvent))
        # Create a uid
        uid = IGlobalIdentifier(self.ob).create()

        # See that the event fired
        self.assertEqual(len(events), 1)

        # Make sure everything's kosher
        ob, event = events[0]
        self.assert_(ob is self.ob)
        self.assert_(IGUIDEvent.providedBy(event))
        self.assertEqual(event.old, None)
        self.assertEqual(event.new, uid)

        # Force a new UID and make sure it's on the event
        newuid = IGlobalIdentifier(self.ob).create(force=True)
        ob, event = events[1]
        self.assertEqual(event.old, uid)
        self.assertEqual(event.new, newuid)

    def test_guid_event_causes_registration(self):
        mgr = IGUIDManager(self.aq_ob)
        uid = '123'
        self.assertEqual(mgr.getPath(uid), None)
        IGlobalIdentifier(self.ob).guid = uid
        self.assertEqual(self.dmd.guid_table[uid], self.ob.getPrimaryUrlPath())

    def test_manager_getters(self):
        mgr = IGUIDManager(self.aq_ob)
        uid = IGlobalIdentifier(self.ob).create()
        self.assertEqual(mgr.getPath(uid), self.ob.getPrimaryUrlPath())
        self.assertEqual(mgr.getObject(uid), self.aq_ob)

    def test_object_create(self):
        newob = Identifiable('newidentifiable', self.dmd)
        self.dmd._setObject('newidentifiable', newob)
        self.assertNotEqual(IGlobalIdentifier(newob).guid, None)
        guid = IGlobalIdentifier(newob).guid
        mgr = IGUIDManager(self.aq_ob)
        self.assertEqual(mgr.getObject(guid), newob)

    def test_object_remove(self):
        newob = Identifiable('newidentifiable', self.dmd)
        self.dmd._setObject('newidentifiable', newob)
        mgr = IGUIDManager(self.aq_ob)
        guid = IGlobalIdentifier(newob).guid
        self.assertEqual(mgr.getObject(guid), newob)
        self.dmd._delObject('newidentifiable')
        self.assertEqual(mgr.getObject(guid), None)

    def test_device_move(self):
        zcml.load_string("""
        <configure xmlns="http://namespaces.zope.org/zope">
            <adapter
                for="Products.ZenModel.Device.Device"
                provides="Products.ZenUtils.guid.interfaces.IGUIDManager"
                factory="Products.ZenUtils.guid.guid.GUIDManager"
                />
        </configure>
        """)
        source = self.dmd.Devices.createOrganizer('source')
        dest = self.dmd.Devices.createOrganizer('dest')
        dev = source.createInstance('testdevice')
        guid = IGlobalIdentifier(dev).guid
        source.moveDevices(dest.getOrganizerName(), 'testdevice')
        newdev = dest.devices.testdevice
        newguid = IGlobalIdentifier(newdev).guid
        self.assertEqual(guid, newguid)


def test_suite():
    return unittest.makeSuite(TestGuid)
