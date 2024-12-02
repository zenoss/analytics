##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import Mock, patch

from ..priority import (
    PrioritySelection,
    ModelingPaused,
    IntEnumFactory,
    ServiceCallPriority,
    ServiceCallPriorityMap,
    servicecall_priority_map,
    _build_weighted_list,
)
from .. import priority

PATH = {"src": "Products.ZenHub.server.priority"}


class TestPrioritySelection(TestCase):
    """Test the PrioritySelection class."""

    def setUp(self):
        self.priorities = ("a", "b", "c")

    def test_without_excluder(self):
        selection = PrioritySelection(self.priorities)
        self.assertSequenceEqual(self.priorities, selection.priorities)
        self.assertSequenceEqual(self.priorities, selection.available)
        expected = (
            "a",
            "a",
            "b",
            "a",
            "a",
            "b",
            "c",
            "a",
            "a",
            "b",
            "a",
        )
        actual = tuple(next(selection) for _ in range(len(expected)))
        self.assertSequenceEqual(expected, actual)

    def test_with_excluder(self):
        def exclude():
            return ("a",)

        selection = PrioritySelection(self.priorities, exclude=exclude)
        self.assertSequenceEqual(self.priorities, selection.priorities)
        self.assertSequenceEqual(("b", "c"), selection.available)
        expected = (
            "b",
            "b",
            "c",
            "b",
        )
        actual = tuple(next(selection) for _ in range(len(expected)))
        self.assertSequenceEqual(expected, actual)

    def test_with_dynamic_excluder(self):
        excluded = ["a"]

        def exclude():
            return excluded

        selection = PrioritySelection(self.priorities, exclude=exclude)
        self.assertSequenceEqual(("b", "c"), selection.available)

        expected = ("b", "b", "c")
        actual = tuple(next(selection) for _ in range(len(expected)))
        self.assertSequenceEqual(expected, actual)

        excluded[:] = []
        self.assertSequenceEqual(("a", "b", "c"), selection.available)
        expected = ("a", "a", "b", "a")
        actual = tuple(next(selection) for _ in range(len(expected)))
        self.assertSequenceEqual(expected, actual)


class ModelingPausedTest(TestCase):
    """Test the ModelingPaused class."""

    def setUp(self):
        self.getUtility_patcher = patch(
            "{src}.getUtility".format(**PATH),
            autospec=True,
        )
        self.getUtility = self.getUtility_patcher.start()
        self.addCleanup(self.getUtility_patcher.stop)

        self.scp = Mock()
        self.ServiceCallPriority_patcher = patch.object(
            priority,
            "ServiceCallPriority",
        )
        self.ServiceCallPriority = self.ServiceCallPriority_patcher.start()
        self.addCleanup(self.ServiceCallPriority_patcher.stop)
        self.MODEL = self.ServiceCallPriority.MODEL

        self.dmd = Mock(spec=["getPauseADMLife"])
        self.dmd_factory = self.getUtility.return_value
        self.dmd_factory.return_value = self.dmd
        self.timeout = 10.0
        self.config = Mock(priorities={"modeling": "MODEL"})

        self.paused = ModelingPaused("MODEL", self.timeout)

    def test_paused(self):
        self.dmd.getPauseADMLife.return_value = 5.0
        expected = [self.MODEL]
        result = self.paused()
        self.assertSequenceEqual(expected, result)

    def test_unpaused(self):
        self.dmd.getPauseADMLife.return_value = 11.0
        expected = []
        result = self.paused()
        self.assertSequenceEqual(expected, result)

    def test_dynamic_pausing(self):
        self.dmd.getPauseADMLife.return_value = 100.0
        expected = []
        self.assertSequenceEqual(expected, self.paused())

        self.dmd.getPauseADMLife.return_value = 6.0
        expected = [self.MODEL]
        self.assertSequenceEqual(expected, self.paused())


class IntEnumFactoryTest(TestCase):
    """Test the IntEnumFactory class."""

    def setUp(self):
        self.names = ("ONE", "TWO", "THREE")
        self.Number = IntEnumFactory.build("Number", self.names)

    def test_attributes(self):
        self.assertTrue(hasattr(self.Number, "ONE"))
        self.assertTrue(hasattr(self.Number, "TWO"))
        self.assertTrue(hasattr(self.Number, "THREE"))

    def test_values(self):
        self.assertEqual(self.Number.ONE, 1)
        self.assertEqual(self.Number.TWO, 2)
        self.assertEqual(self.Number.THREE, 3)

    def test_ordering(self):
        self.assertLess(self.Number.ONE, self.Number.TWO)
        self.assertLess(self.Number.TWO, self.Number.THREE)
        self.assertLess(self.Number.ONE, self.Number.THREE)
        self.assertGreater(self.Number.TWO, self.Number.ONE)
        self.assertGreater(self.Number.THREE, self.Number.TWO)
        self.assertGreater(self.Number.THREE, self.Number.ONE)
        self.assertNotEqual(self.Number.ONE, self.Number.TWO)
        self.assertNotEqual(self.Number.ONE, self.Number.THREE)
        self.assertNotEqual(self.Number.TWO, self.Number.THREE)


class ServiceCallPriorityMapTest(TestCase):
    """Test the ServiceCallPriorityMap class."""

    def setUp(self):
        self.priorities = ("ONE", "TWO", "THREE")
        self.Priority = IntEnumFactory.build("Priority", self.priorities)
        self.mapping = {
            "ServiceOne:foo": "ONE",
            "ServiceTwo:bar": "TWO",
            "Remote.ServiceThree:*": "ONE",
            "*:*": "THREE",
            "*:baz": "TWO",
        }
        self.priority_map = ServiceCallPriorityMap(
            self.mapping,
            self.Priority,
        )

    def test_missing_default_map(self):
        mapping = {
            "path:one": "ONE",
            "path:two": "TWO",
            "road:one": "THREE",
        }
        with self.assertRaises(ValueError):
            ServiceCallPriorityMap(mapping, self.Priority)

    def test_get(self):
        tests = (
            (("ServiceOne", "foo"), self.Priority.ONE),
            (("ServiceOne", "bar"), self.Priority.THREE),
            (("ServiceOne", "baz"), self.Priority.TWO),
            (("ServiceTwo", "foo"), self.Priority.THREE),
            (("ServiceTwo", "bar"), self.Priority.TWO),
            (("ServiceTwo", "baz"), self.Priority.TWO),
            (("Remote.ServiceThree", "f"), self.Priority.ONE),
            (("Remote.ServiceThree", "g"), self.Priority.ONE),
            (("Remote.ServiceThree", "baz"), self.Priority.ONE),
            (("Other.Service", "baz"), self.Priority.TWO),
            (("Other.Service", "foo"), self.Priority.THREE),
        )
        for key, expected in tests:
            result = self.priority_map.get(key)
            self.assertEqual(
                expected,
                result,
                "for key {}, {!r} != {!r}".format(key, expected, result),
            )

    def test_get_default(self):
        default = object()
        expected = default
        result = self.priority_map.get(("Blah", "run"), default)
        self.assertEqual(expected, result)

    def test_index_lookup(self):
        tests = (
            (("ServiceOne", "foo"), self.Priority.ONE),
            (("ServiceOne", "bar"), self.Priority.THREE),
            (("ServiceOne", "baz"), self.Priority.TWO),
            (("ServiceTwo", "foo"), self.Priority.THREE),
            (("ServiceTwo", "bar"), self.Priority.TWO),
            (("ServiceTwo", "baz"), self.Priority.TWO),
            (("Remote.ServiceThree", "f"), self.Priority.ONE),
            (("Remote.ServiceThree", "g"), self.Priority.ONE),
            (("Remote.ServiceThree", "baz"), self.Priority.ONE),
            (("Other.Service", "baz"), self.Priority.TWO),
            (("Other.Service", "foo"), self.Priority.THREE),
        )
        for key, expected in tests:
            result = self.priority_map[key]
            self.assertEqual(
                expected,
                result,
                "for key {}, {!r} != {!r}".format(key, expected, result),
            )

    def test_len(self):
        self.assertEqual(len(self.mapping), len(self.priority_map))

    def test_iteration(self):
        expected = sorted(self.mapping)
        actual = sorted(self.priority_map)
        self.assertSequenceEqual(expected, actual)


class BuildPriorityListTest(TestCase):
    """Test the _build_weighted_list function."""

    def test_one_priority(self):
        expected = (1,)
        actual = _build_weighted_list([1])
        self.assertSequenceEqual(expected, actual)

    def test_two_priorities(self):
        expected = (1, 1, 2, 1)
        actual = _build_weighted_list([1, 2])
        self.assertSequenceEqual(expected, actual)

    def test_three_priorities(self):
        expected = (
            1,
            1,
            2,
            1,
            1,
            2,
            3,
            1,
            1,
            2,
            1,
        )
        actual = _build_weighted_list([1, 2, 3])
        self.assertSequenceEqual(expected, actual)

    def test_four_priorities(self):
        expected = (
            1,
            1,
            2,
            1,
            1,
            2,
            3,
            1,
            1,
            2,
            1,
            1,
            2,
            3,
            4,
            1,
            1,
            2,
            1,
            1,
            2,
            3,
            1,
            1,
            2,
            1,
        )
        actual = _build_weighted_list([1, 2, 3, 4])
        self.assertSequenceEqual(expected, actual)


class ConfiguredPrioritiesTest(TestCase):
    """Test the ServiceCallPriority enumeration."""

    def test_has_required_priority_names(self):
        expected = {"OTHER", "EVENTS", "SINGLE_MODELING", "MODELING", "CONFIG"}
        actual = {p.name for p in ServiceCallPriority}
        self.assertSetEqual(actual, expected)

    def test_has_required_priority_ordering(self):
        expected = [
            ServiceCallPriority.EVENTS,
            ServiceCallPriority.SINGLE_MODELING,
            ServiceCallPriority.OTHER,
            ServiceCallPriority.CONFIG,
            ServiceCallPriority.MODELING,
        ]
        actual = sorted(ServiceCallPriority)
        self.assertSequenceEqual(expected, actual)


class ConfiguredServiceCallPriorityMapTest(TestCase):
    """Test the servicecall_priority_map object."""

    def test_has_required_message_mapping(self):
        expected_mapping = {
            ("EventService", "sendEvent"): ServiceCallPriority.EVENTS,
            ("EventService", "sendEvents"): ServiceCallPriority.EVENTS,
            (
                "ZenPacks.zenoss.PythonCollector.PythonConfig",
                "applyDataMaps",
            ): ServiceCallPriority.MODELING,
            (
                "ModelerService",
                "singleApplyDataMaps",
            ): ServiceCallPriority.SINGLE_MODELING,
            ("Package.ServiceOne", "doThis"): ServiceCallPriority.OTHER,
            ("Package.ServiceTwo", "doThat"): ServiceCallPriority.OTHER,
            (
                "Package.ServiceOne",
                "getDeviceConfigs",
            ): ServiceCallPriority.CONFIG,
            (
                "Package.ServiceOne",
                "getDeviceConfig",
            ): ServiceCallPriority.CONFIG,
        }
        for mesg, expected in expected_mapping.iteritems():
            actual = servicecall_priority_map.get(mesg)
            self.assertEqual(
                actual,
                expected,
                "Message '%s' should map to %s, not %s"
                % (
                    mesg,
                    expected.name,
                    actual.name,
                ),
            )
        # Catch to ensure this test is updated for new priorities
        available = set(ServiceCallPriority)
        used = set(expected_mapping.values())
        self.assertSetEqual(available - used, set())
