##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import transaction

from OFS.interfaces import IItem
from Testing.ZopeTestCase.layer import ZopeLite
from Zope2.App import zcml
from zope import component, interface
from zope.component.hooks import setHooks
from zope.component.interfaces import IObjectEvent
from zope.testing import cleanup

from Products.ZenRelations.RelationshipBase import IRelationship
from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenTestCase.BaseTestCase import (
    BaseTestCase,
    init_model_catalog_for_tests,
)
from Products.ZenUtils.ZenDocTest import load_unittest_site


class EventLogger(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self._called = []

    def trace(self, ob, event):
        self._called.append((ob.getId(), event.__class__.__name__))

    def called(self):
        return self._called

    def print_called(self):
        from pprint import pprint

        pprint(self.called())


eventlog = EventLogger()


class ITestItem(interface.Interface):
    pass


@interface.implementer(ITestItem, IItem)
class TestItem(RelationshipManager):
    def __init__(self, id):
        self.id = id
        self.buildRelations()


TS = "Products.ZenRelations.tests.testEvents."


class TestParentContainer(TestItem):
    _relations = (
        ("contained", ToManyCont(ToOne, TS + "TestToManyCont", "container")),
    )


class TestToManyCont(TestItem):
    _relations = (
        ("contained", ToManyCont(ToOne, TS + "TestContained", "container")),
        (
            "container",
            ToOne(ToManyCont, TS + "TestParentContainer", "contained"),
        ),
    )


class TestContained(TestItem):
    _relations = (
        ("container", ToOne(ToManyCont, TS + "TestToManyCont", "contained")),
    )


def setUpEventlog(iface=None):
    eventlog.reset()
    component.provideHandler(eventlog.trace, (iface, IObjectEvent))
    return eventlog


class EventLayer(ZopeLite):
    @classmethod
    def setUp(cls):
        import Products  # noqa F401

        load_unittest_site(force=True)
        setHooks()

        # Register Model Catalog related stuff
        init_model_catalog_for_tests()

        component.provideHandler(eventlog.trace, (ITestItem, IObjectEvent))
        component.provideHandler(eventlog.trace, (IRelationship, IObjectEvent))

    @classmethod
    def tearDown(cls):
        cleanup.cleanUp()


class EventTest(BaseTestCase):

    layer = EventLayer


class TestToManyContRelationship(EventTest):
    def afterSetUp(self):
        super(TestToManyContRelationship, self).afterSetUp()

        self.app._setObject("root", TestToManyCont("root"))
        self.root = getattr(self.app, "root")
        transaction.savepoint(1)
        eventlog.reset()

    def testToManyContAdding(self):
        self.root.contained._setObject("ob1", TestContained("ob1"))
        self.assertEqual(
            eventlog.called(),
            [
                # Addition of ToOneRelationship
                ("container", "ObjectWillBeAddedEvent"),
                ("container", "ObjectAddedEvent"),
                ("ob1", "ContainerModifiedEvent"),
                # Addition of the RelationshipManager to ToManyCont
                ("container", "ObjectWillBeAddedEvent"),
                ("ob1", "ObjectWillBeAddedEvent"),
                ("container", "ObjectAddedEvent"),
                ("ob1", "ObjectAddedEvent"),
            ],
        )

    def testToManyContDeleteContained(self):
        self.root.contained._setObject("ob1", TestContained("ob1"))
        eventlog.reset()
        self.root.contained._delObject("ob1")
        self.assertEqual(
            eventlog.called(),
            [
                ("container", "ObjectWillBeRemovedEvent"),
                ("ob1", "ObjectWillBeRemovedEvent"),
                ("container", "ObjectRemovedEvent"),
                ("ob1", "ObjectRemovedEvent"),
            ],
        )

    def testToManyContDeleteContainer(self):
        self.app._setObject("grandpa", TestParentContainer("grandpa"))
        grandpa = getattr(self.app, "grandpa")
        grandpa.contained._setObject("pops", TestToManyCont("pops"))
        pops = getattr(grandpa.contained, "pops")
        pops.contained._setObject("sonny", TestContained("sonny"))
        eventlog.reset()
        grandpa.contained._delObject("pops")
        self.assertEqual(
            eventlog.called(),
            [
                ("contained", "ObjectWillBeRemovedEvent"),
                ("container", "ObjectWillBeRemovedEvent"),
                ("sonny", "ObjectWillBeRemovedEvent"),
                ("container", "ObjectWillBeRemovedEvent"),
                ("pops", "ObjectWillBeRemovedEvent"),
                ("contained", "ObjectRemovedEvent"),
                ("container", "ObjectRemovedEvent"),
                ("sonny", "ObjectRemovedEvent"),
                ("container", "ObjectRemovedEvent"),
                ("pops", "ObjectRemovedEvent"),
            ],
        )


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestToManyContRelationship))
    return suite
