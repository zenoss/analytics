##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# runtests -v -t unit Products.ZenEvents -m testTrapFilter

import logging

from unittest import TestCase

from mock import Mock

from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenHub.interfaces import TRANSFORM_CONTINUE, TRANSFORM_DROP

from ..filterspec import (
    FilterSpecification,
    GenericTrapFilterDefinition,
    V1FilterDefinition,
    V2FilterDefinition,
)
from ..trapfilter import TrapFilter


class TrapFilterTest(TestCase):
    def setUp(t):
        t.app = Mock()
        t.monitor = "localhost"
        t.spec = FilterSpecification(t.monitor)
        t.filter = TrapFilter(t.app, t.spec)
        logging.disable(logging.CRITICAL)

    def tearDown(t):
        logging.disable(logging.NOTSET)

    def testDropV1EventForGenericTrapInclusion(t):
        genericTrap = 0
        filterDef = GenericTrapFilterDefinition(99, "include", genericTrap)
        t.filter._filterspec._v1Traps[genericTrap] = filterDef

        event = {"snmpVersion": "1", "snmpV1GenericTrapType": genericTrap}
        t.assertFalse(t.filter._dropEvent(event))

    def testDropV1EventForGenericTrapForExclusion(t):
        genericTrap = 1
        filterDef = GenericTrapFilterDefinition(99, "exclude", genericTrap)
        t.filter._filterspec._v1Traps[genericTrap] = filterDef

        event = {"snmpVersion": "1", "snmpV1GenericTrapType": genericTrap}
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForGenericTrapForNoMatch(t):
        genericTrap = 1
        filterDef = GenericTrapFilterDefinition(99, "exclude", genericTrap)
        t.filter._filterspec._v1Traps[genericTrap] = filterDef

        event = {"snmpVersion": "1", "snmpV1GenericTrapType": 2}
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForEnterpriseSimpleGlobMatch(t):
        filterDef = V1FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[4] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3.4",
        }
        t.assertTrue(t.filter._dropEvent(event))

        filterDef.action = "include"
        t.assertFalse(t.filter._dropEvent(event))

    # This test uses 1 filters for each of two OID levels where the filter
    # specifies a glob match
    def testDropV1EventForSimpleGlobMatches(t):
        filterDef = V1FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[4] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.2.3.4.5.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[6] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3.4",
        }
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.99"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.99.5"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4.99"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5.99"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.99.4"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.99.4.5.6"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventIncludeAll(t):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1",
        }
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1."
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3"
        t.assertFalse(t.filter._dropEvent(event))

    def testDropV1EventExcludeAll(t):
        filterDef = V1FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1",
        }
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventExcludeAllBut(t):
        filterDef = V1FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[4] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.4.5")
        filterDef.specificTrap = "*"
        filtersByLevel = {"1.4.5-*": filterDef}
        t.filter._filterspec._v1Filters[3] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1",
        }
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.4.5.1"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.4.5"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.4.5"
        event["snmpV1SpecificTrap"] = 23
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5"
        t.assertFalse(t.filter._dropEvent(event))

    def testDropV1EventIncludeAllBut(t):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        filterDef = V1FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[4] = filtersByLevel

        filterDef = V1FilterDefinition(99, "exclude", "1.4.5")
        filterDef.specificTrap = "*"
        filtersByLevel = {"1.4.5-*": filterDef}
        t.filter._filterspec._v1Filters[3] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1",
        }
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.4.5.1"
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.4.5"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4.5"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForInvalidGenericTrap(t):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 9,
            "snmpV1Enterprise": "1.2",
        }
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForMissingGenericTrap(t):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        event = {"snmpVersion": "1", "snmpV1Enterprise": "1.2"}
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForMissingEnterpriseOID(t):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
        }
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForEnterpriseAllExcept(t):
        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "*"
        filtersByLevel = {"1.2.3-*": filterDef}
        t.filter._filterspec._v1Filters[3] = filtersByLevel

        filterDef = V1FilterDefinition(99, "exclude", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel["1.2.3-59"] = filterDef

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59,
        }
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1SpecificTrap"] = 99
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV1EventForEnterpriseSpecific(t):
        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel = {"1.2.3-59": filterDef}
        t.filter._filterspec._v1Filters[3] = filtersByLevel

        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "60"
        filtersByLevel["1.2.3-60"] = filterDef

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59,
        }
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1SpecificTrap"] = 60
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpV1SpecificTrap"] = 1
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2.3.4"
        t.assertTrue(t.filter._dropEvent(event))

        event["snmpV1Enterprise"] = "1.2"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV2EventForSimpleExactMatch(t):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3.4")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[4] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3.4"}
        t.assertTrue(t.filter._dropEvent(event))

        filterDef.action = "include"
        t.assertFalse(t.filter._dropEvent(event))

    def testDropV2EventForSimpleGlobMatch(t):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[4] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3.4"}
        t.assertTrue(t.filter._dropEvent(event))

        filterDef.action = "include"
        t.assertFalse(t.filter._dropEvent(event))

    # This test uses 1 filters for each of two OID levels where the filter
    # specifies an exact match
    def testDropV2EventForSimpleExactMatches(t):
        filterDef = V2FilterDefinition(99, "include", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[3] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.2.3.4")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[4] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3"}
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4"
        t.assertFalse(t.filter._dropEvent(event))

        # OIDs with fewer or more levels than the existing filters
        # should NOT match
        event["oid"] = "1.2"
        t.assertTrue(t.filter._dropEvent(event))
        event["oid"] = "1.2.3.4.9"
        t.assertTrue(t.filter._dropEvent(event))

        # OIDs that differ only in the last level should NOT match
        event["oid"] = "1.2.9"
        t.assertTrue(t.filter._dropEvent(event))
        event["oid"] = "1.2.3.9"
        t.assertTrue(t.filter._dropEvent(event))

    # This test uses 1 filters for each of two OID levels where the filter
    # specifies a glob match
    def testDropV2EventForSimpleGlobMatches(t):
        filterDef = V2FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[4] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.2.3.4.5.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[6] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1.2.3.4"}
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.99"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.99.5"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4.99"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4.5"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4.5.99"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.3"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.99.4"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.99.4.5.6"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV2EventIncludeAll(t):
        filterDef = V2FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[1] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1."
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3"
        t.assertFalse(t.filter._dropEvent(event))

    def testDropV2EventExcludeAll(t):
        filterDef = V2FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[1] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.3"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropV2EventExcludeAllBut(t):
        filterDef = V2FilterDefinition(99, "exclude", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[1] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[4] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "1.4.5")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[3] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.3"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.4.5.1"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.4.5"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4.5"
        t.assertFalse(t.filter._dropEvent(event))

    def testDropV2EventIncludeAllBut(t):
        filterDef = V2FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[1] = filtersByLevel

        filterDef = V2FilterDefinition(99, "exclude", "1.2.3.*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[4] = filtersByLevel

        filterDef = V2FilterDefinition(99, "exclude", "1.4.5")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[3] = filtersByLevel

        event = {"snmpVersion": "2", "oid": "1"}
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.2.3"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.4.5.1"
        t.assertFalse(t.filter._dropEvent(event))

        event["oid"] = "1.4.5"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4"
        t.assertTrue(t.filter._dropEvent(event))

        event["oid"] = "1.2.3.4.5"
        t.assertTrue(t.filter._dropEvent(event))

    def testDropEvent(t):
        filterDef = V1FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v1Filters[1] = filtersByLevel

        filterDef = V2FilterDefinition(99, "include", "*")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[1] = filtersByLevel

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59,
        }
        t.assertFalse(t.filter._dropEvent(event))

        event = {
            "snmpVersion": "2",
            "oid": "1.2.3",
        }
        t.assertFalse(t.filter._dropEvent(event))

        event["snmpVersion"] = "invalidVersion"
        t.assertTrue(t.filter._dropEvent(event))

    def testTransformPassesV1Event(t):
        filterDef = V1FilterDefinition(99, "include", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel = {"1.2.3-59": filterDef}
        t.filter._filterspec._v1Filters[3] = filtersByLevel
        t.filter._filterspec._filtersDefined = True

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": filterDef.oid,
            "snmpV1SpecificTrap": filterDef.specificTrap,
        }
        t.assertEquals(TRANSFORM_CONTINUE, t.filter.transform(event))

    def testTransformDropsV1Event(t):
        filterDef = V1FilterDefinition(99, "exclude", "1.2.3")
        filterDef.specificTrap = "59"
        filtersByLevel = {"1.2.3-59": filterDef}
        t.filter._app.counters = {
            "eventCount": 0,
            "eventFilterDroppedCount": 0,
        }
        t.filter._filterspec._v1Filters[3] = filtersByLevel
        t.filter._filterspec._filtersDefined = True

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": filterDef.oid,
            "snmpV1SpecificTrap": filterDef.specificTrap,
        }
        t.assertEquals(TRANSFORM_DROP, t.filter.transform(event))

    def testTransformPassesV2Event(t):
        filterDef = V2FilterDefinition(99, "include", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[3] = filtersByLevel
        t.filter._filterspec._filtersDefined = True

        event = {
            "snmpVersion": "2",
            "oid": filterDef.oid,
        }
        t.assertEquals(TRANSFORM_CONTINUE, t.filter.transform(event))

    def testTransformPassesV3Event(t):
        filterDef = V2FilterDefinition(99, "include", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._filterspec._v2Filters[3] = filtersByLevel
        t.filter._filterspec._filtersDefined = True

        event = {
            "snmpVersion": "3",
            "oid": filterDef.oid,
        }
        t.assertEquals(TRANSFORM_CONTINUE, t.filter.transform(event))

    def testTransformDropsV2Event(t):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._app.counters = {
            "eventCount": 0,
            "eventFilterDroppedCount": 0,
        }
        t.filter._filterspec._v2Filters[3] = filtersByLevel
        t.filter._filterspec._filtersDefined = True

        event = {
            "snmpVersion": "2",
            "oid": filterDef.oid,
        }
        t.assertEquals(TRANSFORM_DROP, t.filter.transform(event))

    def testTransformDropsV3Event(t):
        filterDef = V2FilterDefinition(99, "exclude", "1.2.3")
        filtersByLevel = {filterDef.oid: filterDef}
        t.filter._app.counters = {
            "eventCount": 0,
            "eventFilterDroppedCount": 0,
        }
        t.filter._filterspec._v2Filters[3] = filtersByLevel
        t.filter._filterspec._filtersDefined = True

        event = {
            "snmpVersion": "3",
            "oid": filterDef.oid,
        }
        t.assertEquals(TRANSFORM_DROP, t.filter.transform(event))

    def testTransformWithoutFilters(t):
        t.filter._filterspec._filtersDefined = False

        event = {
            "snmpVersion": "1",
            "snmpV1GenericTrapType": 6,
            "snmpV1Enterprise": "1.2.3",
            "snmpV1SpecificTrap": 59,
        }
        t.assertEquals(TRANSFORM_CONTINUE, t.filter.transform(event))

        event = {
            "snmpVersion": "2",
            "oid": "1.2.3",
        }
        t.assertEquals(TRANSFORM_CONTINUE, t.filter.transform(event))

    def testTrapFilterDefaultParse(t):
        t.spec.update_from_string(EventManagerBase.trapFilters)
        # t.assertEquals(t.filter._eventService.sendEvent.called, False)
        t.assertEquals(len(t.filter._filterspec._v1Traps), 6)
        t.assertEquals(len(t.filter._filterspec._v1Filters), 1)
        t.assertEquals(len(t.filter._filterspec._v2Filters), 1)

    def testTrapFilterParseCollectorMatch(t):
        filterCfg = "localhost exclude v2 1.3.6.1.2.1.43.18.2.0.1"
        t.spec.update_from_string(filterCfg)
        # t.assertEquals(t.filter._eventService.sendEvent.called, False)
        t.assertEquals(len(t.filter._filterspec._v2Filters), 1)

    def testTrapFilterParseCollectorNotMatch(t):
        filterCfg = "remoteDMZ exclude v2 1.3.6.1.2.1.43.18.2.0.1"
        t.spec.update_from_string(filterCfg)
        # t.assertEquals(t.filter._eventService.sendEvent.called, False)
        t.assertEquals(len(t.filter._filterspec._v2Filters), 0)


# def test_suite():
#     from unittest import TestSuite, makeSuite
# 
#     suite = TestSuite()
#     suite.addTest(makeSuite(TrapFilterTest))
#     return suite
