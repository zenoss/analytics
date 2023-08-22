##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

#runtests -v -t unit Products.ZenEvents -m testZentrap

from mock import Mock

from Products.ZenEvents.EventManagerBase import EventManagerBase

from Products.ZenEvents.TrapFilter import BaseFilterDefinition
from Products.ZenEvents.TrapFilter import OIDBasedFilterDefinition
from Products.ZenEvents.TrapFilter import GenericTrapFilterDefinition
from Products.ZenEvents.TrapFilter import V1FilterDefinition
from Products.ZenEvents.TrapFilter import V2FilterDefinition
from Products.ZenEvents.TrapFilter import TrapFilter
from Products.ZenHub.interfaces import \
    TRANSFORM_CONTINUE, \
    TRANSFORM_DROP
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class OIDBasedFilterDefinitionTest(BaseTestCase):
    def testEQByOID(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        self.assert_(base1 == base2)

    def testEQByOIDFails(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "5.4.3.2.1")
        self.assert_(base1 != base2)

    def testEQByOIDIgnoresAction(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "exclude", "1.2.3.4.5")
        self.assert_(base1 == base2)

    def testEQByOIDFailsForDifferentClass(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = BaseFilterDefinition(0, "include")
        self.assert_(base1 != base2)

    def testHash(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        self.assert_(base1.__hash__() == base2.__hash__())

    def testHashFails(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "5.4.3.2.1")
        self.assert_(base1.__hash__() != base2.__hash__())

    def testHashIgnoresAction(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "exclude", "1.2.3.4.5")
        self.assert_(base1.__hash__() == base2.__hash__())

class GenericTrapFilterDefinitionTest(BaseTestCase):
    def testEQByOID(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "1")
        self.assert_(base1 == base2)

    def testEQByOIDFails(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "5")
        self.assert_(base1 != base2)

    def testEQByOIDIgnoresAction(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "exclude", "1")
        self.assert_(base1 == base2)

    def testEQByOIDFailsForDifferentClass(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = BaseFilterDefinition(0, "include")
        self.assert_(base1 != base2)

    def testHash(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "1")
        self.assertEquals(base1.__hash__(), base2.__hash__())

    def testHashFails(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "2")
        self.assertNotEquals(base1.__hash__(), base2.__hash__())

    def testHashIgnoresAction(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "exclude", "1")
        self.assert_(base1.__hash__() == base2.__hash__())


class TrapFilterTest(BaseTestCase):
    def testValidateOIDForGlob(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._validateOID("*")
        self.assertEquals(results, None)

        results = filter._validateOID("1.2.*")
        self.assertEquals(results, None)

    def testValidateOIDFailsForEmptyString(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._validateOID("")
        self.assertEquals(results, "Empty OID is invalid")

    def testValidateOIDFailsForSimpleNumber(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._validateOID("123")
        self.assertEquals(results, "At least one '.' required")

    def testValidateOIDFailsForInvalidChars(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._validateOID("1.2.3-5.*")
        self.assertEquals(results, "Invalid character found; only digits, '.' and '*' allowed")

    def testValidateOIDFailsForDoubleDots(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._validateOID("1.2..3")
        self.assertEquals(results, "Consecutive '.'s not allowed")

    def testValidateOIDFailsForInvalidGlobbing(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._validateOID("1.2.3.*.5.*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("1.*.5")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("1.5*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*.")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*.1")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*.*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("5*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*5")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID(".*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

    def testParseFilterDefinitionForEmptyLine(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, "Incomplete filter definition")

    def testParseFilterDefinitionForIncompleteLine(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("a b", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, "Incomplete filter definition")

    def testParseFilterDefinitionForInvalidAction(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("invalid V1 ignored", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, "Invalid action 'invalid'; the only valid actions are 'include' or 'exclude'")

    def testParseFilterDefinitionForInvalidVersion(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V4 ignored", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, "Invalid SNMP version 'V4'; the only valid versions are 'v1' or 'v2' or 'v3'")

    def testParseFilterDefinitionForInvalidV1Definition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V1 .", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForCaseInsensitiveDefinition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("InClude v1 3", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, None)

    def testParseFilterDefinitionForValidV1Definition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V1 3", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, None)

    def testParseFilterDefinitionForInvalidV2Definition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V2 .", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForValidV2Definition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V2 .1.3.6.1.4.*", 99)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(results, None)

    def testParseFilterDefinitionForInvalidV3Definition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V3 .", 99)
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForValidV3Definition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseFilterDefinition("include V3 .1.3.6.1.4.*", 99)
        self.assertEquals(results, None)

    def testParseV1FilterDefinitionForGenericTrap(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", ["0"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 1)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 0)

        genericTrapDefinition = filter._v1Traps["0"]
        self.assert_(genericTrapDefinition != None)
        self.assertEquals(genericTrapDefinition.lineNumber, 99)
        self.assertEquals(genericTrapDefinition.action, "include")
        self.assertEquals(genericTrapDefinition.genericTrap, "0")

        # Now add another to make sure we can parse more than one
        results = filter._parseV1FilterDefinition(100, "exclude", ["5"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 2)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 0)

        genericTrapDefinition = filter._v1Traps["5"]
        self.assert_(genericTrapDefinition != None)
        self.assertEquals(genericTrapDefinition.lineNumber, 100)
        self.assertEquals(genericTrapDefinition.action, "exclude")
        self.assertEquals(genericTrapDefinition.genericTrap, "5")

    def testParseV1FilterDefinitionEnterpriseSpecificTrap(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", ["1.2.3.*"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 1)
        self.assertEquals(len(filter._v2Filters), 0)

        oidLevels = 4
        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["1.2.3.*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 99)
        self.assertEquals(filterDef.action, "include")
        self.assertEquals(filterDef.oid, "1.2.3.*")
        self.assertEquals(filterDef.specificTrap, None)

        # Add another 4-level OID
        results = filter._parseV1FilterDefinition(100, "exclude", ["1.2.3.4", "25"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 1)
        self.assertEquals(len(filter._v2Filters), 0)

        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 2)

        filterDef = mapByLevel["1.2.3.4-25"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 100)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "1.2.3.4")
        self.assertEquals(filterDef.specificTrap, "25")

        # Add a different specific trap for the same OID
        results = filter._parseV1FilterDefinition(101, "exclude", ["1.2.3.4", "99"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 1)
        self.assertEquals(len(filter._v2Filters), 0)

        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 3)

        filterDef = mapByLevel["1.2.3.4-99"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 101)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "1.2.3.4")
        self.assertEquals(filterDef.specificTrap, "99")

        # Add another single-level OID
        results = filter._parseV1FilterDefinition(101, "exclude", ["*"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 2)
        self.assertEquals(len(filter._v2Filters), 0)

        oidLevels = 1
        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 101)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "*")
        self.assertEquals(filterDef.specificTrap, None)

    def testParseV1FilterDefinitionFailsForTooManyArgs(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", ["0", "1", "2"], ".*")
        self.assertEquals(results, "Too many fields found; at most 4 fields allowed for V1 filters")

    def testParseV1FilterDefinitionFailsForEmptyOID(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", [], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV1FilterDefinition(99, "include", [""], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV1FilterDefinition(99, "include", ["."], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV1FilterDefinition(99, "include", ["..."], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseV1FilterDefinitionFailsForInvalidOID(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", ["invalidOID"], ".*")
        self.assertEquals(results, "'invalidOID' is not a valid OID: Invalid character found; only digits, '.' and '*' allowed")

    def testParseV1FilterDefinitionFailsForInvalidTrap(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", ["a"], ".*")
        self.assertEquals(results, "Invalid generic trap 'a'; must be one of 0-5")

        results = filter._parseV1FilterDefinition(99, "include", ["6"], ".*")
        self.assertEquals(results, "Invalid generic trap '6'; must be one of 0-5")

    def testParseV1FilterDefinitionFailsForConflictingTrap(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", ["1"], ".*")
        self.assertEquals(results, None)

        results = filter._parseV1FilterDefinition(100, "include", ["1"], ".*")
        self.assertEquals(results, "Generic trap '1' conflicts with previous definition at line 99")

        # Verify we find a conflict for generic traps where the action differs
        results = filter._parseV1FilterDefinition(100, "exclude", ["1"], ".*")
        self.assertEquals(results, "Generic trap '1' conflicts with previous definition at line 99")

    def testParseV1FilterDefinitionFailsForConflictingOID(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5", "2"], ".*")
        self.assertEquals(results, None)

        results = filter._parseV1FilterDefinition(100, "include", [".1.3.6.1.4.5", "2"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        # Verify we find a conflict for OIDs where the action differs
        results = filter._parseV1FilterDefinition(100, "exclude", [".1.3.6.1.4.5", "2"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        results = filter._parseV1FilterDefinition(101, "include", [".1.3.6.1.4.*"], ".*")
        self.assertEquals(results, None)

        # Verify we find a conflict for glob-based OIDs
        results = filter._parseV1FilterDefinition(102, "include", [".1.3.6.1.4.*"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

        # Verify we find a conflict for glob-based OIDs where the action differs
        results = filter._parseV1FilterDefinition(102, "exclude", [".1.3.6.1.4.*"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

    def testParseV1FilterDefinitionFailsForEnterpriseSpecificGlob(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5.*", "23"], ".*")
        self.assertEquals(results, "Specific trap not allowed with globbed OID")

    def testParseV1FilterDefinitionFailsForInvalidEnterpriseSpecificTrap(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5", "abc"], ".*")
        self.assertEquals(results, "Specific trap 'abc' invalid; must be non-negative integer")

        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5", "-1"], ".*")
        self.assertEquals(results, "Specific trap '-1' invalid; must be non-negative integer")

    def testParseV1FilterDefinitionForSpecificOid(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5"], ".*")
        self.assertEquals(results, None)

    def testParseV2FilterDefinition(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV2FilterDefinition(99, "include", ["1.2.3.*"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 1)

        oidLevels = 4
        mapByLevel = filter._v2Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["1.2.3.*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 99)
        self.assertEquals(filterDef.action, "include")
        self.assertEquals(filterDef.oid, "1.2.3.*")

        # Add another 4-level OID
        results = filter._parseV2FilterDefinition(100, "exclude", ["1.2.3.4"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 1)

        mapByLevel = filter._v2Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 2)

        filterDef = mapByLevel["1.2.3.4"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 100)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "1.2.3.4")

        # Add another single-level OID
        results = filter._parseV2FilterDefinition(101, "exclude", ["*"], ".*")
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 2)

        oidLevels = 1
        mapByLevel = filter._v2Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 101)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "*")

    def testParseV2FilterDefinitionFailsForTooManyArgs(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV2FilterDefinition(99, "include", ["0", "1"], ".*")
        self.assertEquals(results, "Too many fields found; at most 3 fields allowed for V2 filters")

    def testParseV2FilterDefinitionFailsForEmptyOID(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV2FilterDefinition(99, "include", [], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV2FilterDefinition(99, "include", [""], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV2FilterDefinition(99, "include", ["."], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV2FilterDefinition(99, "include", ["..."], ".*")
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseV2FilterDefinitionFailsForInvalidOID(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV2FilterDefinition(99, "include", ["invalidOID"], ".*")
        self.assertEquals(results, "'invalidOID' is not a valid OID: Invalid character found; only digits, '.' and '*' allowed")

    def testParseV2FilterDefinitionFailsForConflictingOID(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        results = filter._parseV2FilterDefinition(99, "include", [".1.3.6.1.4.5"], ".*")
        self.assertEquals(results, None)

        results = filter._parseV2FilterDefinition(100, "include", [".1.3.6.1.4.5"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        # Verify we find a conflict for OIDs where the action differs
        results = filter._parseV2FilterDefinition(100, "exclude", [".1.3.6.1.4.5"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        results = filter._parseV2FilterDefinition(101, "include", [".1.3.6.1.4.*"], ".*")
        self.assertEquals(results, None)

        # Verify we find a conflict for glob-based OIDs
        results = filter._parseV2FilterDefinition(102, "include", [".1.3.6.1.4.*"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

        # Verify we find a conflict for glob-based OIDs where the action differs
        results = filter._parseV2FilterDefinition(102, "exclude", [".1.3.6.1.4.*"], ".*")
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

    def testDropV1EventForGenericTrapInclusion(self):
        genericTrap = 0
        filterDef = GenericTrapFilterDefinition(99, "include", genericTrap)
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Traps[genericTrap] = filterDef

        event = {"snmpVersion": "1", "snmpV1GenericTrapType": genericTrap}
        self.assertFalse(filter._dropV1Event(event))

    def testDropV1EventForGenericTrapForExclusion(self):
        genericTrap = 1
        filterDef = GenericTrapFilterDefinition(99, "exclude", genericTrap)
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Traps[genericTrap] = filterDef

        event = {"snmpVersion": "1", "snmpV1GenericTrapType": genericTrap}
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForGenericTrapForNoMatch(self):
        genericTrap = 1
        filterDef = GenericTrapFilterDefinition(99, "exclude", genericTrap)
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Traps[genericTrap] = filterDef

        event = {"snmpVersion": "1", "snmpV1GenericTrapType": 2}
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForEnterpriseSimpleGlobMatch(self):
        filterDef = V1FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[4] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3.4"
        }
        self.assertTrue(filter._dropV1Event(event))

        filterDef.action = "include"
        self.assertFalse(filter._dropV1Event(event))

    # This test uses 1 filters for each of two OID levels where the filter specifies a glob match
    def testDropV1EventForSimpleGlobMatches(self):
        filterDef = V1FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[4] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.2.3.4.5.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v1Filters[6] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3.4"
        }
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.99"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.99.5"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4.99"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5.99"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.99.4"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.99.4.5.6"
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventIncludeAll(self):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1"
        }
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1."
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3"
        self.assertFalse(filter._dropV1Event(event))

    def testDropV1EventExcludeAll(self):
        filterDef = V1FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1"
        }
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3"
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventExcludeAllBut(self):
        filterDef = V1FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v1Filters[4] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.4.5")
        filterDef.specificTrap = "*"
        filtersByLevel = {"1.4.5-*": filterDef}
        filter._v1Filters[3] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1"
        }
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.4.5.1"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.4.5"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.4.5"
        event["snmpV1SpecificTrap"] = 23
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5"
        self.assertFalse(filter._dropV1Event(event))

    def testDropV1EventIncludeAllBut(self):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        filterDef = V1FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v1Filters[4] = filtersByLevel

        filterDef = V1FilterDefinition(99, "exclude", "1.4.5")
        filterDef.specificTrap = "*"
        filtersByLevel = {"1.4.5-*": filterDef}
        filter._v1Filters[3] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1"
        }
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.4.5.1"
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.4.5"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5"
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForInvalidGenericTrap(self):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 9,
            "snmpV1Enterprise": "1.2"
        }
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForMissingGenericTrap(self):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1Enterprise": "1.2"
        }
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForMissingEnterpriseOID(self):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
        }
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForEnterpriseAllExcept(self):
        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "*"
        filtersByLevel = {"1.2.3-*": filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[3] = filtersByLevel

        filterDef = V1FilterDefinition(99, "exclude", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel["1.2.3-59"] = filterDef

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59
        }
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1SpecificTrap"] = 99
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2"
        self.assertTrue(filter._dropV1Event(event))

    def testDropV1EventForEnterpriseSpecific(self):
        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel = {"1.2.3-59": filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[3] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "60"
        filtersByLevel["1.2.3-60"] = filterDef

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59
        }
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1SpecificTrap"] = 60
        self.assertFalse(filter._dropV1Event(event))

        event["snmpV1SpecificTrap"] = 1
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        self.assertTrue(filter._dropV1Event(event))

        event["snmpV1Enterprise"] = "1.2"
        self.assertTrue(filter._dropV1Event(event))

    def testDropV2EventForSimpleExactMatch(self):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3.4")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[4] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3.4"}
        self.assertTrue(filter._dropV2Event(event))

        filterDef.action = "include"
        self.assertFalse(filter._dropV2Event(event))

    def testDropV2EventForSimpleGlobMatch(self):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[4] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3.4"}
        self.assertTrue(filter._dropV2Event(event))

        filterDef.action = "include"
        self.assertFalse(filter._dropV2Event(event))

    # This test uses 1 filters for each of two OID levels where the filter specifies an exact match
    def testDropV2EventForSimpleExactMatches(self):
        filterDef = V2FilterDefinition(99, "include", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[3] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.2.3.4")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[4] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3"}
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4"
        self.assertFalse(filter._dropV2Event(event))

        # OIDs with fewer or more levels than the existing filters should NOT match
        event["oid"] = "1.2"
        self.assertTrue(filter._dropV2Event(event))
        event["oid"] = "1.2.3.4.9"
        self.assertTrue(filter._dropV2Event(event))

        # OIDs that differ only in the last level should NOT match
        event["oid"] = "1.2.9"
        self.assertTrue(filter._dropV2Event(event))
        event["oid"] = "1.2.3.9"
        self.assertTrue(filter._dropV2Event(event))

    # This test uses 1 filters for each of two OID levels where the filter specifies a glob match
    def testDropV2EventForSimpleGlobMatches(self):
        filterDef = V2FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[4] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.2.3.4.5.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[6] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3.4"}
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.99"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.99.5"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4.99"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4.5"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4.5.99"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.3"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.99.4"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.99.4.5.6"
        self.assertTrue(filter._dropV2Event(event))

    def testDropV2EventIncludeAll(self):
        filterDef = V2FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[1] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1."
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3"
        self.assertFalse(filter._dropV2Event(event))

    def testDropV2EventExcludeAll(self):
        filterDef = V2FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[1] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.3"
        self.assertTrue(filter._dropV2Event(event))

    def testDropV2EventExcludeAllBut(self):
        filterDef = V2FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[1] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[4] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.4.5")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[3] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.3"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.4.5.1"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.4.5"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4.5"
        self.assertFalse(filter._dropV2Event(event))

    def testDropV2EventIncludeAllBut(self):
        filterDef = V2FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[1] = filtersByLevel

        filterDef = V2FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[4] = filtersByLevel

        filterDef = V2FilterDefinition(99, "exclude", "1.4.5")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[3] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.2.3"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.4.5.1"
        self.assertFalse(filter._dropV2Event(event))

        event["oid"] = "1.4.5"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4"
        self.assertTrue(filter._dropV2Event(event))

        event["oid"] = "1.2.3.4.5"
        self.assertTrue(filter._dropV2Event(event))

    def testDropEvent(self):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[1] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        filter._v2Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59
        }
        self.assertFalse(filter._dropEvent(event))

        event = {
            "snmpVersion": "2",
            "oid": "1.2.3",
        }
        self.assertFalse(filter._dropEvent(event))

        event["snmpVersion"] = "invalidVersion"
        self.assertTrue(filter._dropEvent(event))

    def testTransformPassesV1Event(self):
        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel = {"1.2.3-59": filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v1Filters[3] = filtersByLevel
        filter._filtersDefined = True

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": filterDef.oid,
            "snmpV1SpecificTrap": filterDef.specificTrap
        }
        self.assertEquals(TRANSFORM_CONTINUE, filter.transform(event))

    def testTransformDropsV1Event(self):
        filterDef = V1FilterDefinition(99, "exclude", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel = {"1.2.3-59": filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._daemon.counters = {
            'eventCount': 0,
            'eventFilterDroppedCount': 0}
        filter._v1Filters[3] = filtersByLevel
        filter._filtersDefined = True

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": filterDef.oid,
            "snmpV1SpecificTrap": filterDef.specificTrap
        }
        self.assertEquals(TRANSFORM_DROP, filter.transform(event))

    def testTransformPassesV2Event(self):
        filterDef = V2FilterDefinition(99, "include", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._v2Filters[3] = filtersByLevel
        filter._filtersDefined = True

        event = {
            "snmpVersion": "2",
            "oid": filterDef.oid,
        }
        self.assertEquals(TRANSFORM_CONTINUE, filter.transform(event))

    def testTransformDropsV2Event(self):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._daemon.counters = {
            'eventCount': 0,
            'eventFilterDroppedCount': 0}
        filter._v2Filters[3] = filtersByLevel
        filter._filtersDefined = True

        event = {
            "snmpVersion": "2",
            "oid": filterDef.oid,
        }
        self.assertEquals(TRANSFORM_DROP, filter.transform(event))

    def testTransformWithoutFilters(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter._filtersDefined = False

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59
        }
        self.assertEquals(TRANSFORM_CONTINUE, filter.transform(event))

        event = {
            "snmpVersion": "2",
            "oid": "1.2.3",
        }
        self.assertEquals(TRANSFORM_CONTINUE, filter.transform(event))

    def testTrapFilterDefaultParse(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filter.updateFilter(EventManagerBase.trapFilters)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(len(filter._v1Traps), 6)
        self.assertEquals(len(filter._v1Filters), 1)
        self.assertEquals(len(filter._v2Filters), 1)

    def testTrapFilterParseCollectorMatch(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filterCfg = "localhost exclude v2 1.3.6.1.2.1.43.18.2.0.1"
        filter.updateFilter(filterCfg)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(len(filter._v2Filters), 1)

    def testTrapFilterParseCollectorNotMatch(self):
        filter = TrapFilter()
        filter._eventService = Mock()
        filter._daemon = Mock()
        filter._daemon.options.monitor = 'localhost'
        filterCfg = "remoteDMZ exclude v2 1.3.6.1.2.1.43.18.2.0.1"
        filter.updateFilter(filterCfg)
        self.assertEquals(filter._eventService.sendEvent.called, False)
        self.assertEquals(len(filter._v2Filters), 0)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(OIDBasedFilterDefinitionTest))
    suite.addTest(makeSuite(GenericTrapFilterDefinitionTest))
    suite.addTest(makeSuite(TrapFilterTest))
    return suite
