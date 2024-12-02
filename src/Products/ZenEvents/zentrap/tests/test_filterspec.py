##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

# runtests -v -t unit Products.ZenEvents -m testTrapFilter

import logging

from unittest import TestCase

from ..filterspec import (
    BaseFilterDefinition,
    FilterSpecification,
    GenericTrapFilterDefinition,
    OIDBasedFilterDefinition,
)


class OIDBasedFilterDefinitionTest(TestCase):
    def testEQByOID(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        self.assertEqual(base1, base2)

    def testEQByOIDFails(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "5.4.3.2.1")
        self.assertNotEqual(base1, base2)

    def testEQByOIDIgnoresAction(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "exclude", "1.2.3.4.5")
        self.assertEqual(base1, base2)

    def testEQByOIDFailsForDifferentClass(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = BaseFilterDefinition(0, "include")
        self.assertNotEqual(base1, base2)

    def testHash(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        self.assertEqual(hash(base1), hash(base2))

    def testHashFails(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "5.4.3.2.1")
        self.assertNotEqual(hash(base1), hash(base2))

    def testHashIgnoresAction(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "exclude", "1.2.3.4.5")
        self.assertEqual(hash(base1), hash(base2))


class GenericTrapFilterDefinitionTest(TestCase):
    def testEQByOID(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "1")
        self.assertEqual(base1, base2)

    def testEQByOIDFails(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "5")
        self.assertNotEqual(base1, base2)

    def testEQByOIDIgnoresAction(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "exclude", "1")
        self.assertEqual(base1, base2)

    def testEQByOIDFailsForDifferentClass(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = BaseFilterDefinition(0, "include")
        self.assertNotEqual(base1, base2)

    def testHash(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "1")
        self.assertEqual(hash(base1), hash(base2))

    def testHashFails(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "2")
        self.assertNotEqual(hash(base1), hash(base2))

    def testHashIgnoresAction(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "exclude", "1")
        self.assertEqual(hash(base1), hash(base2))


class FilterSpecificationTest(TestCase):
    def setUp(t):
        logging.disable(logging.CRITICAL)
        t.spec = FilterSpecification("localhost")

    def tearDown(t):
        logging.disable(logging.NOTSET)

    def testValidateOIDForGlob(t):
        results = t.spec._validateOID("*")
        t.assertEqual(results, None)

        results = t.spec._validateOID("1.2.*")
        t.assertEqual(results, None)

    def testValidateOIDFailsForEmptyString(t):
        results = t.spec._validateOID("")
        t.assertEqual(results, "Empty OID is invalid")

    def testValidateOIDFailsForSimpleNumber(t):
        results = t.spec._validateOID("123")
        t.assertEqual(results, "At least one '.' required")

    def testValidateOIDFailsForInvalidChars(t):
        results = t.spec._validateOID("1.2.3-5.*")
        t.assertEqual(
            results,
            "Invalid character found; only digits, '.' and '*' allowed",
        )

    def testValidateOIDFailsForDoubleDots(t):
        results = t.spec._validateOID("1.2..3")
        t.assertEqual(results, "Consecutive '.'s not allowed")

    def testValidateOIDFailsForInvalidGlobbing(t):
        results = t.spec._validateOID("1.2.3.*.5.*")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("1.*.5")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("1.5*")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("*.")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("*.1")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("*.*")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("5*")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID("*5")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

        results = t.spec._validateOID(".*")
        t.assertEqual(
            results,
            "When using '*', only a single '*' at the end of OID is allowed",
        )

    def testParseFilterDefinitionForEmptyLine(t):
        results = t.spec._parseFilterDefinition("", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, "Incomplete filter definition")

    def testParseFilterDefinitionForIncompleteLine(t):
        results = t.spec._parseFilterDefinition("a b", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, "Incomplete filter definition")

    def testParseFilterDefinitionForInvalidAction(t):
        results = t.spec._parseFilterDefinition("invalid V1 ignored", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(
            results,
            "Invalid action 'invalid'; the only valid actions are "
            "'include' or 'exclude'",
        )

    def testParseFilterDefinitionForInvalidVersion(t):
        results = t.spec._parseFilterDefinition("include V4 ignored", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(
            results,
            "Invalid SNMP version 'V4'; the only valid versions are "
            "'v1', 'v2', or 'v3'",
        )

    def testParseFilterDefinitionForInvalidV1Definition(t):
        results = t.spec._parseFilterDefinition("include V1 .", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForCaseInsensitiveDefinition(t):
        results = t.spec._parseFilterDefinition("InClude v1 3", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, None)

    def testParseFilterDefinitionForValidV1Definition(t):
        results = t.spec._parseFilterDefinition("include V1 3", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, None)

    def testParseFilterDefinitionForInvalidV2Definition(t):
        results = t.spec._parseFilterDefinition("include V2 .", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForValidV2Definition(t):
        results = t.spec._parseFilterDefinition("include V2 .1.3.6.1.4.*", 99)
        # t.assertEqual(t.spec._eventService.sendEvent.called, False)
        t.assertEqual(results, None)

    def testParseFilterDefinitionForInvalidV3Definition(t):
        results = t.spec._parseFilterDefinition("include V3 .", 99)
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForValidV3Definition(t):
        results = t.spec._parseFilterDefinition("include V3 .1.3.6.1.4.*", 99)
        t.assertEqual(results, None)

    def testParseV1FilterDefinitionForGenericTrap(t):
        results = t.spec._parseV1FilterDefinition(99, "include", ["0"], ".*")
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 1)
        t.assertEqual(len(t.spec._v1Filters), 0)
        t.assertEqual(len(t.spec._v2Filters), 0)

        genericTrapDefinition = t.spec._v1Traps["0"]
        t.assertIsNotNone(genericTrapDefinition)
        t.assertEqual(genericTrapDefinition.lineNumber, 99)
        t.assertEqual(genericTrapDefinition.action, "include")
        t.assertEqual(genericTrapDefinition.genericTrap, "0")

        # Now add another to make sure we can parse more than one
        results = t.spec._parseV1FilterDefinition(100, "exclude", ["5"], ".*")
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 2)
        t.assertEqual(len(t.spec._v1Filters), 0)
        t.assertEqual(len(t.spec._v2Filters), 0)

        genericTrapDefinition = t.spec._v1Traps["5"]
        t.assertIsNotNone(genericTrapDefinition)
        t.assertEqual(genericTrapDefinition.lineNumber, 100)
        t.assertEqual(genericTrapDefinition.action, "exclude")
        t.assertEqual(genericTrapDefinition.genericTrap, "5")

    def testParseV1FilterDefinitionEnterpriseSpecificTrap(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", ["1.2.3.*"], ".*"
        )
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 1)
        t.assertEqual(len(t.spec._v2Filters), 0)

        oidLevels = 4
        mapByLevel = t.spec._v1Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 1)

        filterDef = mapByLevel["1.2.3.*"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 99)
        t.assertEqual(filterDef.action, "include")
        t.assertEqual(filterDef.oid, "1.2.3.*")
        t.assertEqual(filterDef.specificTrap, None)

        # Add another 4-level OID
        results = t.spec._parseV1FilterDefinition(
            100, "exclude", ["1.2.3.4", "25"], ".*"
        )
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 1)
        t.assertEqual(len(t.spec._v2Filters), 0)

        mapByLevel = t.spec._v1Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 2)

        filterDef = mapByLevel["1.2.3.4-25"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 100)
        t.assertEqual(filterDef.action, "exclude")
        t.assertEqual(filterDef.oid, "1.2.3.4")
        t.assertEqual(filterDef.specificTrap, "25")

        # Add a different specific trap for the same OID
        results = t.spec._parseV1FilterDefinition(
            101, "exclude", ["1.2.3.4", "99"], ".*"
        )
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 1)
        t.assertEqual(len(t.spec._v2Filters), 0)

        mapByLevel = t.spec._v1Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 3)

        filterDef = mapByLevel["1.2.3.4-99"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 101)
        t.assertEqual(filterDef.action, "exclude")
        t.assertEqual(filterDef.oid, "1.2.3.4")
        t.assertEqual(filterDef.specificTrap, "99")

        # Add another single-level OID
        results = t.spec._parseV1FilterDefinition(101, "exclude", ["*"], ".*")
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 2)
        t.assertEqual(len(t.spec._v2Filters), 0)

        oidLevels = 1
        mapByLevel = t.spec._v1Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 1)

        filterDef = mapByLevel["*"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 101)
        t.assertEqual(filterDef.action, "exclude")
        t.assertEqual(filterDef.oid, "*")
        t.assertEqual(filterDef.specificTrap, None)

    def testParseV1FilterDefinitionFailsForTooManyArgs(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", ["0", "1", "2"], ".*"
        )
        t.assertEqual(
            results,
            "Too many fields found; at most 4 fields allowed for V1 filters",
        )

    def testParseV1FilterDefinitionFailsForEmptyOID(t):
        results = t.spec._parseV1FilterDefinition(99, "include", [], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

        results = t.spec._parseV1FilterDefinition(99, "include", [""], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

        results = t.spec._parseV1FilterDefinition(99, "include", ["."], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

        results = t.spec._parseV1FilterDefinition(99, "include", ["..."], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseV1FilterDefinitionFailsForInvalidOID(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", ["invalidOID"], ".*"
        )
        t.assertEqual(
            results,
            "'invalidOID' is not a valid OID: Invalid character found; "
            "only digits, '.' and '*' allowed",
        )

    def testParseV1FilterDefinitionFailsForInvalidTrap(t):
        results = t.spec._parseV1FilterDefinition(99, "include", ["a"], ".*")
        t.assertEqual(results, "Invalid generic trap 'a'; must be one of 0-5")

        results = t.spec._parseV1FilterDefinition(99, "include", ["6"], ".*")
        t.assertEqual(results, "Invalid generic trap '6'; must be one of 0-5")

    def testParseV1FilterDefinitionFailsForConflictingTrap(t):
        results = t.spec._parseV1FilterDefinition(99, "include", ["1"], ".*")
        t.assertEqual(results, None)

        results = t.spec._parseV1FilterDefinition(100, "include", ["1"], ".*")
        t.assertEqual(
            results,
            "Generic trap '1' conflicts with previous definition at line 99",
        )

        # Verify we find a conflict for generic traps where the action differs
        results = t.spec._parseV1FilterDefinition(100, "exclude", ["1"], ".*")
        t.assertEqual(
            results,
            "Generic trap '1' conflicts with previous definition at line 99",
        )

    def testParseV1FilterDefinitionFailsForConflictingOID(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", [".1.3.6.1.4.5", "2"], ".*"
        )
        t.assertEqual(results, None)

        results = t.spec._parseV1FilterDefinition(
            100, "include", [".1.3.6.1.4.5", "2"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.5' conflicts with previous definition at line 99",
        )

        # Verify we find a conflict for OIDs where the action differs
        results = t.spec._parseV1FilterDefinition(
            100, "exclude", [".1.3.6.1.4.5", "2"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.5' conflicts with previous definition at line 99",
        )

        results = t.spec._parseV1FilterDefinition(
            101, "include", [".1.3.6.1.4.*"], ".*"
        )
        t.assertEqual(results, None)

        # Verify we find a conflict for glob-based OIDs
        results = t.spec._parseV1FilterDefinition(
            102, "include", [".1.3.6.1.4.*"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.*' conflicts with previous definition at line 101",
        )

        # Verify we find a conflict for glob-based OIDs where the
        # action differs.
        results = t.spec._parseV1FilterDefinition(
            102, "exclude", [".1.3.6.1.4.*"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.*' conflicts with previous definition at line 101",
        )

    def testParseV1FilterDefinitionFailsForEnterpriseSpecificGlob(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", [".1.3.6.1.4.5.*", "23"], ".*"
        )
        t.assertEqual(results, "Specific trap not allowed with globbed OID")

    def testParseV1FilterDefinitionFailsForInvalidEnterpriseSpecificTrap(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", [".1.3.6.1.4.5", "abc"], ".*"
        )
        t.assertEqual(
            results,
            "Specific trap 'abc' invalid; must be non-negative integer",
        )

        results = t.spec._parseV1FilterDefinition(
            99, "include", [".1.3.6.1.4.5", "-1"], ".*"
        )
        t.assertEqual(
            results, "Specific trap '-1' invalid; must be non-negative integer"
        )

    def testParseV1FilterDefinitionForSpecificOid(t):
        results = t.spec._parseV1FilterDefinition(
            99, "include", [".1.3.6.1.4.5"], ".*"
        )
        t.assertEqual(results, None)

    def testParseV2FilterDefinition(t):
        results = t.spec._parseV2FilterDefinition(
            99, "include", ["1.2.3.*"], ".*"
        )
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 0)
        t.assertEqual(len(t.spec._v2Filters), 1)

        oidLevels = 4
        mapByLevel = t.spec._v2Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 1)

        filterDef = mapByLevel["1.2.3.*"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 99)
        t.assertEqual(filterDef.action, "include")
        t.assertEqual(filterDef.oid, "1.2.3.*")

        # Add another 4-level OID
        results = t.spec._parseV2FilterDefinition(
            100, "exclude", ["1.2.3.4"], ".*"
        )
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 0)
        t.assertEqual(len(t.spec._v2Filters), 1)

        mapByLevel = t.spec._v2Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 2)

        filterDef = mapByLevel["1.2.3.4"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 100)
        t.assertEqual(filterDef.action, "exclude")
        t.assertEqual(filterDef.oid, "1.2.3.4")

        # Add another single-level OID
        results = t.spec._parseV2FilterDefinition(101, "exclude", ["*"], ".*")
        t.assertEqual(results, None)
        t.assertEqual(len(t.spec._v1Traps), 0)
        t.assertEqual(len(t.spec._v1Filters), 0)
        t.assertEqual(len(t.spec._v2Filters), 2)

        oidLevels = 1
        mapByLevel = t.spec._v2Filters[oidLevels]
        t.assertIsNotNone(mapByLevel)
        t.assertEqual(len(mapByLevel), 1)

        filterDef = mapByLevel["*"]
        t.assertIsNotNone(filterDef)
        t.assertEqual(filterDef.lineNumber, 101)
        t.assertEqual(filterDef.action, "exclude")
        t.assertEqual(filterDef.oid, "*")

    def testParseV2FilterDefinitionFailsForTooManyArgs(t):
        results = t.spec._parseV2FilterDefinition(
            99, "include", ["0", "1"], ".*"
        )
        t.assertEqual(
            results,
            "Too many fields found; at most 3 fields allowed for V2 filters",
        )

    def testParseV2FilterDefinitionFailsForEmptyOID(t):
        results = t.spec._parseV2FilterDefinition(99, "include", [], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

        results = t.spec._parseV2FilterDefinition(99, "include", [""], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

        results = t.spec._parseV2FilterDefinition(99, "include", ["."], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

        results = t.spec._parseV2FilterDefinition(99, "include", ["..."], ".*")
        t.assertEqual(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseV2FilterDefinitionFailsForInvalidOID(t):
        results = t.spec._parseV2FilterDefinition(
            99, "include", ["invalidOID"], ".*"
        )
        t.assertEqual(
            results,
            "'invalidOID' is not a valid OID: Invalid character found; "
            "only digits, '.' and '*' allowed",
        )

    def testParseV2FilterDefinitionFailsForConflictingOID(t):
        results = t.spec._parseV2FilterDefinition(
            99, "include", [".1.3.6.1.4.5"], ".*"
        )
        t.assertEqual(results, None)

        results = t.spec._parseV2FilterDefinition(
            100, "include", [".1.3.6.1.4.5"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.5' conflicts with previous definition at line 99",
        )

        # Verify we find a conflict for OIDs where the action differs
        results = t.spec._parseV2FilterDefinition(
            100, "exclude", [".1.3.6.1.4.5"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.5' conflicts with previous definition at line 99",
        )

        results = t.spec._parseV2FilterDefinition(
            101, "include", [".1.3.6.1.4.*"], ".*"
        )
        t.assertEqual(results, None)

        # Verify we find a conflict for glob-based OIDs
        results = t.spec._parseV2FilterDefinition(
            102, "include", [".1.3.6.1.4.*"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.*' conflicts with previous definition at line 101",
        )

        # Verify we find a conflict for glob-based OIDs where the
        # action differs
        results = t.spec._parseV2FilterDefinition(
            102, "exclude", [".1.3.6.1.4.*"], ".*"
        )
        t.assertEqual(
            results,
            "OID '1.3.6.1.4.*' conflicts with previous definition at line 101",
        )


class TestPersistentFilterSpecProperties(TestCase):
    """
    Test that the `v1traps`, `v1filters`, and `v2filters` properties are
    updated after a call to `update_from_string` with a different config.
    """

    _rules_v1 = "\n".join(
        (
            "include v1 0",
            "include v1 1",
            "include v1 2",
            "include v1 3",
            "include v1 4",
            "include v1 5",
            "include v1 *",
            "include v2 *",
        )
    )

    _rules_v2 = "\n".join(
        (
            "include v1 0",
            "include v1 1",
            "exclude v1 2",
            "include v1 3",
            "include v1 4",
            "include v1 5",
            "include v1 *",
            "include v2 *",
            "exclude v1 1.3.6.1.4.1.9.9.41.2.0.*",
            "exclude v2 1.3.6.1.4.1.9.9.43.1.3.*",
        )
    )

    def setUp(t):
        t.spec = FilterSpecification("localhost")
        t.spec.update_from_string(t._rules_v1)

    def test_v1trap_property(t):
        reference = t.spec.v1traps
        original = dict(reference)
        t.spec.update_from_string(t._rules_v2)

        t.assertEqual(len(original), len(t.spec.v1traps))
        t.assertEqual(len(reference), len(t.spec.v1traps))
        t.assertFalse(
            all(
                (kr == kl) and _eq_v1generic(vr, vl)
                for (kr, vr), (kl, vl) in zip(
                    sorted(original.items()), sorted(t.spec.v1traps.items())
                )
            )
        )
        t.assertTrue(
            all(
                (kr == kl) and _eq_v1generic(vr, vl)
                for (kr, vr), (kl, vl) in zip(
                    sorted(reference.items()), sorted(t.spec.v1traps.items())
                )
            )
        )

    def test_v1filters_property(t):
        reference = t.spec.v1filters
        original = dict(reference)
        t.spec.update_from_string(t._rules_v2)

        t.assertNotEqual(len(original), len(t.spec.v1filters))
        t.assertEqual(len(reference), len(t.spec.v1filters))
        t.assertTrue(
            all(
                (kr == kl) and _eq_v1enterprise(vr, vl)
                for (kr, vr), (kl, vl) in zip(
                    sorted(reference.items()), sorted(t.spec.v1filters.items())
                )
            )
        )

    def test_v2filters_property(t):
        reference = t.spec.v2filters
        original = dict(reference)
        t.spec.update_from_string(t._rules_v2)

        t.assertNotEqual(len(original), len(t.spec.v2filters))
        t.assertEqual(len(reference), len(t.spec.v2filters))
        t.assertTrue(
            all(
                (kr == kl) and _eq_v2(vr, vl)
                for (kr, vr), (kl, vl) in zip(
                    sorted(reference.items()), sorted(t.spec.v2filters.items())
                )
            )
        )


def _eq_v1generic(lv, rv):
    return (lv.genericTrap == rv.genericTrap) and (lv.action == rv.action)


def _eq_v1enterprise(lv, rv):
    return all(
        (k1 == k2)
        and (v1.action == v2.action)
        and (v1.oid == v2.oid)
        and (v1.specificTrap == v2.specificTrap)
        for (k1, v1), (k2, v2) in zip(sorted(lv.items()), sorted(rv.items()))
    )


def _eq_v2(lv, rv):
    return all(
        (k1 == k2)
        and (v1.action == v2.action)
        and (v1.oid == v2.oid)
        for (k1, v1), (k2, v2) in zip(sorted(lv.items()), sorted(rv.items()))
    )
