##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
import uuid

from zope.interface import implementer

from Products.ZenMessaging.queuemessaging.publisher import ModelChangePublisher
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier


@implementer(IGlobalIdentifier)
class MockIGlobalIdentifier(object):
    def __init__(self):
        self._guid = None
        self.create()

    def getGUID(self):
        return self._guid

    def setGUID(self, value):
        self._guid = value

    def create(self, force=False):
        if self._guid is None or force:
            self._guid = str(uuid.uuid4())
        return self._guid

    guid = property(getGUID, setGUID)


class TestModelChangePublisher(BaseTestCase):
    """
    See docstrings on ModelChangePublisher for expected invariants
    """

    def afterSetUp(self):
        super(TestModelChangePublisher, self).afterSetUp()
        self.mcp = ModelChangePublisher()

    def assertInvariants(self, objects):
        intersection = set(self.mcp._removedGuids) & set(self.mcp._addedGuids)
        self.assertEqual(
            intersection,
            set(),
            "Guids present in both added, removed: %s" % intersection,
        )

        union = set(self.mcp._removedGuids) | set(self.mcp._addedGuids)
        for obj in objects:
            self.assertIn(
                obj.guid,
                union,
                "Guid %s not in removed or added: %s" % (obj.guid, union),
            )

            messages = [
                msg
                for msg in self.mcp._msgs
                if msg[1][0] == obj and msg[1][1] in ("ADDED", "REMOVED")
            ]
            self.assertEqual(
                len(messages),
                1,
                "More than one message found for guid %s: %s"
                % (obj.guid, messages),
            )

    def assertAddedInvariants(self, addedObjects):
        for obj in addedObjects:
            self.assertIn(
                obj.guid,
                self.mcp._addedGuids,
                "Guid %s not in added" % obj.guid,
            )

            messages = [
                msg
                for msg in self.mcp._msgs
                if msg[1][0] == obj and msg[1][1] == "ADDED"
            ]
            self.assertEqual(
                len(messages),
                1,
                "No ADDED message found for guid %s: %s"
                % (obj.guid, messages),
            )

    def assertRemovedInvariants(self, removedObjects):
        for obj in removedObjects:
            self.assertIn(
                obj.guid,
                self.mcp._removedGuids,
                "Guid %s not in removed" % obj.guid,
            )

            messages = [
                msg
                for msg in self.mcp._msgs
                if msg[1][0] == obj and msg[1][1] == "REMOVED"
            ]
            self.assertEqual(
                len(messages),
                1,
                "No REMOVED message found for guid %s: %s"
                % (obj.guid, messages),
            )

    def assertTotal(self, total):
        self.assertEqual(
            self.mcp._total,
            total,
            "Total messages incorrect, %d instead of %d"
            % (self.mcp._total, total),
        )

    def testPublishAdd(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishAdd(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([testObj])
        self.assertRemovedInvariants([])
        self.assertTotal(1)

    def testPublishRemove(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishRemove(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([])
        self.assertRemovedInvariants([testObj])
        self.assertTotal(1)

    def testAdd2Removes(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)
        self.mcp.publishRemove(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([])
        self.assertRemovedInvariants([testObj])
        self.assertTotal(3)

    def testRemove2Adds(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)
        self.mcp.publishAdd(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([testObj])
        self.assertRemovedInvariants([])
        self.assertTotal(3)

    def test2AddsRemove(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishAdd(testObj)
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([])
        self.assertRemovedInvariants([testObj])
        self.assertTotal(3)

    def test2RemovesAdd(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishRemove(testObj)
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([testObj])
        self.assertRemovedInvariants([])
        self.assertTotal(3)

    def testRemoveAddFlap(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([testObj])
        self.assertRemovedInvariants([])
        self.assertTotal(6)

    def testAddRemoveFlap(self):
        testObj = MockIGlobalIdentifier()
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)
        self.mcp.publishAdd(testObj)
        self.mcp.publishRemove(testObj)

        self.assertInvariants([testObj])
        self.assertAddedInvariants([])
        self.assertRemovedInvariants([testObj])
        self.assertTotal(6)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestModelChangePublisher))
    return suite


if __name__ == "__main__":
    unittest.main()
