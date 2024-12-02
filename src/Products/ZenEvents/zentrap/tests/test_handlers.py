import logging

from unittest import TestCase

import six

from mock import Mock

from ..handlers import ReplayTrapHandler
from ..net import FakePacket, SNMPv1, SNMPv2
from ..oidmap import OidMap
from ..processors import (
    LegacyVarbindProcessor,
    DirectVarbindProcessor,
    MixedVarbindProcessor,
)


class _Common(TestCase):
    def setUp(t):
        logging.disable(logging.CRITICAL)
        t.app = Mock()
        t.oidmap = OidMap(t.app)
        t.eventservice = Mock()
        t.stats = Mock()
        t.monitor = "localhost"

    def tearDown(t):
        logging.disable(logging.NOTSET)


class _SnmpV1Base(_Common):
    def makeInputs(t, trapType=6, oidMap=None, variables=(), copymode=None):
        oidMap = oidMap if oidMap is not None else {}
        pckt = FakePacket()
        pckt.version = SNMPv1
        pckt.host = "localhost"
        pckt.port = 162
        pckt.variables = variables
        pckt.community = ""
        pckt.enterprise_length = 0

        # extra fields for SNMPv1 packets
        pckt.agent_addr = [192, 168, 24, 4]
        pckt.trap_type = trapType
        pckt.specific_type = 5
        pckt.enterprise = "1.2.3.4"
        pckt.enterprise_length = len(pckt.enterprise)
        pckt.community = "community"

        t.oidmap._oidmap = oidMap
        handler = ReplayTrapHandler(
            t.oidmap, copymode, t.monitor, t.eventservice
        )
        handler.stats = t.stats
        return pckt, handler


class TestDecodeSnmpV1(_SnmpV1Base):
    def test_NoAgentAddr(t):
        pckt, handler = t.makeInputs()
        del pckt.agent_addr
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(result["device"], "localhost")

    def test_FieldsNoMappingUsed(t):
        pckt, handler = t.makeInputs()
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)

        t.assertEqual(result["device"], "192.168.24.4")
        t.assertEqual(result["snmpVersion"], "1")
        t.assertEqual(result["snmpV1Enterprise"], "1.2.3.4")
        t.assertEqual(result["snmpV1GenericTrapType"], 6)
        t.assertEqual(result["snmpV1SpecificTrap"], 5)
        t.assertEqual(eventType, "1.2.3.4.5")
        t.assertEqual(result["oid"], "1.2.3.4.5")

    def test_EnterpriseOIDWithExtraZero(t):
        pckt, handler = t.makeInputs(oidMap={"1.2.3.4.0.5": "testing"})
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "testing")
        t.assertEqual(result["oid"], "1.2.3.4.0.5")

    def test_TrapType0(t):
        pckt, handler = t.makeInputs(trapType=0)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "coldStart")
        t.assertEqual(result["snmpV1GenericTrapType"], 0)

    def test_TrapType1(t):
        pckt, handler = t.makeInputs(trapType=1)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "warmStart")
        t.assertEqual(result["snmpV1GenericTrapType"], 1)

    def test_TrapType2(t):
        pckt, handler = t.makeInputs(trapType=2)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "snmp_linkDown")
        t.assertEqual(result["snmpV1GenericTrapType"], 2)

    def test_TrapType3(t):
        pckt, handler = t.makeInputs(trapType=3)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "snmp_linkUp")
        t.assertEqual(result["snmpV1GenericTrapType"], 3)

    def test_TrapType4(t):
        pckt, handler = t.makeInputs(trapType=4)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "authenticationFailure")
        t.assertEqual(result["snmpV1GenericTrapType"], 4)

    def test_TrapType5(t):
        pckt, handler = t.makeInputs(trapType=5)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "egpNeighorLoss")
        t.assertEqual(result["snmpV1GenericTrapType"], 5)

    def test_TrapType6(t):
        pckt, handler = t.makeInputs(trapType=6)
        eventType, result = handler.decodeSnmpv1(("localhost", 162), pckt)
        t.assertEqual(eventType, "1.2.3.4.5")
        t.assertEqual(result["snmpV1GenericTrapType"], 6)


class _SnmpV2Base(_Common):
    baseOidMap = {
        # Std var binds in SnmpV2 traps/notifications
        "1.3.6.1.2.1.1.3": "sysUpTime",
        "1.3.6.1.6.3.1.1.4.1": "snmpTrapOID",
        # SnmpV2 Traps (snmpTrapOID.0 values)
        "1.3.6.1.6.3.1.1.5.1": "coldStart",
        "1.3.6.1.6.3.1.1.5.2": "warmStart",
        "1.3.6.1.6.3.1.1.5.3": "linkDown",
        "1.3.6.1.6.3.1.1.5.4": "linkUp",
        "1.3.6.1.6.3.1.1.5.5": "authenticationFailure",
        "1.3.6.1.6.3.1.1.5.6": "egpNeighborLoss",
    }

    def makePacket(t, trapOID, variables=()):
        pckt = FakePacket()
        pckt.version = SNMPv2
        pckt.host = "localhost"
        pckt.port = 162

        if isinstance(trapOID, six.string_types):
            trapOID = tuple(map(int, trapOID.split(".")))
        pckt.variables = [
            ((1, 3, 6, 1, 2, 1, 1, 3, 0), 5342),
            ((1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0), trapOID),
        ]
        pckt.variables.extend(variables)
        pckt.community = "public"
        pckt.enterprise_length = 0
        return pckt

    def makeHandler(t, extraOidMap=None, copymode=None):
        oidmap = t.baseOidMap.copy()
        if extraOidMap:
            oidmap.update(extraOidMap)
        t.oidmap._oidmap = oidmap
        handler = ReplayTrapHandler(
            t.oidmap, copymode, t.monitor, t.eventservice
        )
        handler.stats = t.stats
        return handler

    def makeInputs(
        t,
        trapOID="1.3.6.1.6.3.1.1.5.1",
        variables=(),
        oidMap=None,
        copymode=None,
    ):
        oidMap = oidMap if oidMap is not None else {}
        pckt = t.makePacket(trapOID=trapOID, variables=variables)
        handler = t.makeHandler(extraOidMap=oidMap, copymode=copymode)
        return pckt, handler


class TestDecodeSnmpV2OrV3(_SnmpV2Base):
    def test_UnknownTrapType(t):
        pckt, handler = t.makeInputs(trapOID="1.2.3")
        eventType, result = handler.decodeSnmpV2OrV3(("localhost", 162), pckt)
        t.assertIn("snmpVersion", result)
        t.assertEqual(result["snmpVersion"], "2")
        t.assertEqual(eventType, "1.2.3")
        t.assertIn("snmpVersion", result)
        t.assertIn("oid", result)
        t.assertIn("device", result)
        t.assertEqual(result["snmpVersion"], "2")
        t.assertEqual(result["oid"], "1.2.3")
        t.assertEqual(result["device"], "localhost")

    def test_KnownTrapType(t):
        pckt, handler = t.makeInputs(trapOID="1.3.6.1.6.3.1.1.5.1")
        eventType, result = handler.decodeSnmpV2OrV3(("localhost", 162), pckt)
        t.assertIn("oid", result)
        t.assertEqual(eventType, "coldStart")
        t.assertEqual(result["oid"], "1.3.6.1.6.3.1.1.5.1")

    def test_TrapAddressOID(t):
        pckt, handler = t.makeInputs(
            trapOID="1.3.6.1.6.3.1.1.5.1",
            variables=(((1, 3, 6, 1, 6, 3, 18, 1, 3), "192.168.51.100"),),
            oidMap={"1.3.6.1.6.3.18.1.3": "snmpTrapAddress"},
        )
        eventType, result = handler.decodeSnmpV2OrV3(("localhost", 162), pckt)
        t.assertIn("snmpTrapAddress", result)
        t.assertEqual(result["snmpTrapAddress"], "192.168.51.100")
        t.assertEqual(result["device"], "192.168.51.100")

    def test_RenamedLinkDown(t):
        pckt, handler = t.makeInputs(trapOID="1.3.6.1.6.3.1.1.5.3")
        eventType, result = handler.decodeSnmpV2OrV3(("localhost", 162), pckt)
        t.assertIn("oid", result)
        t.assertEqual(eventType, "snmp_linkDown")
        t.assertEqual(result["oid"], "1.3.6.1.6.3.1.1.5.3")

    def test_RenamedLinkUp(t):
        pckt, handler = t.makeInputs(trapOID="1.3.6.1.6.3.1.1.5.4")
        eventType, result = handler.decodeSnmpV2OrV3(("localhost", 162), pckt)
        t.assertIn("oid", result)
        t.assertEqual(eventType, "snmp_linkUp")
        t.assertEqual(result["oid"], "1.3.6.1.6.3.1.1.5.4")

    def test_PartialNamedVarBindNoneValue(t):
        pckt = t.makePacket("1.3.6.1.6.3.1.1.5.3")
        pckt.variables.append(
            ((1, 2, 6, 0), None),
        )
        t.oidmap._oidmap = {"1.2.6.0": "testVar"}
        handler = ReplayTrapHandler(
            t.oidmap, None, t.monitor, t.eventservice
        )
        handler.stats = t.stats
        eventType, result = handler.decodeSnmpV2OrV3(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        t.assertEqual(totalVarKeys, 1)
        t.assertIn("testVar", result)
        t.assertEqual(result["testVar"], "None")


class _VarbindTests(object):
    def case_unknown_id_single(t):
        variables = (((1, 2, 6, 7), "foo"),)
        tests = (
            t.makeInputs(
                variables=variables, copymode=MixedVarbindProcessor.MODE
            ),
            t.makeInputs(
                variables=variables, copymode=DirectVarbindProcessor.MODE
            ),
            t.makeInputs(
                variables=variables, copymode=LegacyVarbindProcessor.MODE
            ),
        )
        for test in tests:
            result = yield test
            totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
            t.assertEqual(totalVarKeys, 1)
            t.assertEqual(result["1.2.6.7"], "foo")

    def case_unknown_id_repeated(t):
        variables = (
            ((1, 2, 6, 7), "foo"),
            ((1, 2, 6, 7), "bar"),
            ((1, 2, 6, 7), "baz"),
        )
        tests = (
            t.makeInputs(
                variables=variables, copymode=MixedVarbindProcessor.MODE
            ),
            t.makeInputs(
                variables=variables, copymode=DirectVarbindProcessor.MODE
            ),
            t.makeInputs(
                variables=variables, copymode=LegacyVarbindProcessor.MODE
            ),
        )
        for test in tests:
            result = yield test
            totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
            t.assertEqual(totalVarKeys, 1)
            t.assertEqual(result["1.2.6.7"], "foo,bar,baz")

    def case_unknown_ids_multiple(t):
        variables = (
            ((1, 2, 6, 0), "foo"),
            ((1, 2, 6, 1), "bar"),
        )
        tests = (
            t.makeInputs(
                variables=variables, copymode=MixedVarbindProcessor.MODE
            ),
            t.makeInputs(
                variables=variables, copymode=DirectVarbindProcessor.MODE
            ),
            t.makeInputs(
                variables=variables, copymode=LegacyVarbindProcessor.MODE
            ),
        )
        expected_results = (
            {
                "1.2.6.0": "foo",
                "1.2.6.1": "bar",
            },
            {
                "1.2.6.0": "foo",
                "1.2.6.1": "bar",
            },
            {
                "1.2.6.0": "foo",
                "1.2.6.1": "bar",
            },
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
            t.assertEqual(totalVarKeys, 2)
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_one_id(t):
        variables = (((1, 2, 6, 7), "foo"),)
        oidMap = {"1.2.6.7": "testVar"}
        tests = (
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {"testVar": "foo"},
            {"testVar": "foo"},
            {"testVar": "foo"},
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
            t.assertEqual(totalVarKeys, 1)
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_one_id_one_sub_id(t):
        oidMap = {"1.2.6": "testVar"}
        variables = (((1, 2, 6, 5), "foo"),)
        tests = (
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {
                "testVar": "foo",
                "testVar.ifIndex": "5",
            },
            {
                "testVar.5": "foo",
                "testVar.sequence": "5",
            },
            {
                "testVar": "foo",
                "testVar.ifIndex": "5",
            },
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(1 for k in result if k.startswith("testVar"))
            t.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_one_id_multiple_sub_ids(t):
        oidMap = {"1.2.6": "testVar"}
        variables_one = (
            ((1, 2, 6, 0), "foo"),
            ((1, 2, 6, 1), "bar"),
            ((1, 2, 6, 2), "baz"),
        )
        variables_two = (
            ((1, 2, 6, 3), "foo"),
            ((1, 2, 6, 3), "bar"),
        )

        tests = (
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {
                "testVar.0": "foo",
                "testVar.1": "bar",
                "testVar.2": "baz",
                "testVar.sequence": "0,1,2",
            },
            {
                "testVar.3": "foo,bar",
                "testVar.sequence": "3,3",
            },
            {
                "testVar.0": "foo",
                "testVar.1": "bar",
                "testVar.2": "baz",
                "testVar.sequence": "0,1,2",
            },
            {
                "testVar.3": "foo,bar",
                "testVar.sequence": "3,3",
            },
            {
                "testVar": "foo,bar,baz",
                "testVar.ifIndex": "0,1,2",
            },
            {
                "testVar": "foo,bar",
                "testVar.ifIndex": "3,3",
            },
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(1 for k in result if k.startswith("testVar"))
            t.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_multiple_ids(t):
        oidMap = {
            "1.2.6": "foo",
            "1.2.7": "bar",
        }
        variables = (
            ((1, 2, 6), "is a foo"),
            ((1, 2, 7), "lower the bar"),
        )
        tests = (
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {
                "foo": "is a foo",
                "bar": "lower the bar",
            },
            {
                "foo": "is a foo",
                "bar": "lower the bar",
            },
            {
                "foo": "is a foo",
                "bar": "lower the bar",
            },
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(
                1 for k in result if k.startswith("bar") or k.startswith("foo")
            )
            t.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_multiple_ids_one_sub_id_each(t):
        oidMap = {
            "1.2.6": "foo",
            "1.2.7": "bar",
        }
        variables_one = (
            ((1, 2, 6, 0), "is a foo"),
            ((1, 2, 7, 2), "lower the bar"),
        )
        variables_two = (
            ((1, 2, 6, 0, 1), "is a foo"),
            ((1, 2, 7, 2, 1), "lower the bar"),
        )
        tests = (
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {
                "foo": "is a foo",
                "foo.ifIndex": "0",
                "bar": "lower the bar",
                "bar.ifIndex": "2",
            },
            {
                "foo": "is a foo",
                "foo.ifIndex": "0.1",
                "bar": "lower the bar",
                "bar.ifIndex": "2.1",
            },
            {
                "foo.0": "is a foo",
                "foo.sequence": "0",
                "bar.2": "lower the bar",
                "bar.sequence": "2",
            },
            {
                "foo.0.1": "is a foo",
                "foo.sequence": "0.1",
                "bar.2.1": "lower the bar",
                "bar.sequence": "2.1",
            },
            {
                "foo": "is a foo",
                "foo.ifIndex": "0",
                "bar": "lower the bar",
                "bar.ifIndex": "2",
            },
            {
                "foo": "is a foo",
                "foo.ifIndex": "0.1",
                "bar": "lower the bar",
                "bar.ifIndex": "2.1",
            },
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(
                1 for k in result if k.startswith("bar") or k.startswith("foo")
            )
            t.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_multiple_ids_multiple_sub_ids(t):
        oidMap = {
            "1.2.6": "foo",
            "1.2.7": "bar",
        }
        variables_one = (
            ((1, 2, 6, 0, 1), "here a foo"),
            ((1, 2, 6, 1, 1), "there a foo"),
            ((1, 2, 7, 2, 1), "lower the bar"),
            ((1, 2, 7, 2, 2), "raise the bar"),
        )
        variables_two = (
            ((1, 2, 6, 0), "here a foo"),
            ((1, 2, 6, 0), "there a foo"),
            ((1, 2, 7, 3), "lower the bar"),
            ((1, 2, 7, 3), "raise the bar"),
        )
        tests = (
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_one,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables_two,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {
                "foo.0.1": "here a foo",
                "foo.1.1": "there a foo",
                "foo.sequence": "0.1,1.1",
                "bar.2.1": "lower the bar",
                "bar.2.2": "raise the bar",
                "bar.sequence": "2.1,2.2",
            },
            {
                "foo.0": "here a foo,there a foo",
                "foo.sequence": "0,0",
                "bar.3": "lower the bar,raise the bar",
                "bar.sequence": "3,3",
            },
            {
                "foo.0.1": "here a foo",
                "foo.1.1": "there a foo",
                "foo.sequence": "0.1,1.1",
                "bar.2.1": "lower the bar",
                "bar.2.2": "raise the bar",
                "bar.sequence": "2.1,2.2",
            },
            {
                "foo.0": "here a foo,there a foo",
                "foo.sequence": "0,0",
                "bar.3": "lower the bar,raise the bar",
                "bar.sequence": "3,3",
            },
            {
                "foo": "here a foo,there a foo",
                "foo.ifIndex": "0.1,1.1",
                "bar": "lower the bar,raise the bar",
                "bar.ifIndex": "2.1,2.2",
            },
            {
                "foo": "here a foo,there a foo",
                "foo.ifIndex": "0,0",
                "bar": "lower the bar,raise the bar",
                "bar.ifIndex": "3,3",
            },
        )
        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(
                1 for k in result if k.startswith("bar") or k.startswith("foo")
            )
            t.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])

    def case_ifentry_trap(t):
        oidMap = {
            "1.3.6.1.2.1.2.2.1.1": "ifIndex",
            "1.3.6.1.2.1.2.2.1.7": "ifAdminStatus",
            "1.3.6.1.2.1.2.2.1.8": "ifOperStatus",
            "1.3.6.1.2.1.2.2.1.2": "ifDescr",
            "1.3.6.1.2.1.31.1.1.1.18": "ifAlias",
        }
        variables = (
            ((1, 3, 6, 1, 2, 1, 2, 2, 1, 1, 143), 143),
            ((1, 3, 6, 1, 2, 1, 2, 2, 1, 7, 143), 2),
            ((1, 3, 6, 1, 2, 1, 2, 2, 1, 8, 143), 2),
            ((1, 3, 6, 1, 2, 1, 2, 2, 1, 2, 143), "F23"),
            ((1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 143), ""),
        )
        tests = (
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=MixedVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=DirectVarbindProcessor.MODE,
            ),
            t.makeInputs(
                variables=variables,
                oidMap=oidMap,
                copymode=LegacyVarbindProcessor.MODE,
            ),
        )
        expected_results = (
            {
                "ifIndex": "143",
                "ifIndex.ifIndex": "143",
                "ifAdminStatus": "2",
                "ifAdminStatus.ifIndex": "143",
                "ifOperStatus": "2",
                "ifOperStatus.ifIndex": "143",
                "ifDescr": "F23",
                "ifDescr.ifIndex": "143",
                "ifAlias": "",
                "ifAlias.ifIndex": "143",
            },
            {
                "ifIndex.143": "143",
                "ifIndex.sequence": "143",
                "ifAdminStatus.143": "2",
                "ifAdminStatus.sequence": "143",
                "ifOperStatus.143": "2",
                "ifOperStatus.sequence": "143",
                "ifDescr.143": "F23",
                "ifDescr.sequence": "143",
                "ifAlias.143": "",
                "ifAlias.sequence": "143",
            },
            {
                "ifIndex": "143",
                "ifIndex.ifIndex": "143",
                "ifAdminStatus": "2",
                "ifAdminStatus.ifIndex": "143",
                "ifOperStatus": "2",
                "ifOperStatus.ifIndex": "143",
                "ifDescr": "F23",
                "ifDescr.ifIndex": "143",
                "ifAlias": "",
                "ifAlias.ifIndex": "143",
            },
        )

        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(
                1
                for k in result
                if k.startswith("ifIndex")
                or k.startswith("ifAdminStatus")
                or k.startswith("ifOperStatus")
                or k.startswith("ifDescr")
                or k.startswith("ifAlias")
            )
            t.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                t.assertIn(key, result)
                t.assertEqual(value, result[key])


class TestSnmpV1VarbindHandling(_SnmpV1Base, _VarbindTests):
    def _execute(t, cases):
        try:
            pckt, handler = next(cases)
            while True:
                eventType, result = handler.decodeSnmpv1(
                    ("localhost", 162), pckt
                )
                pckt, handler = cases.send(result)
        except StopIteration:
            pass

    def test_unknown_id_single(t):
        t._execute(t.case_unknown_id_single())

    def test_unknown_id_repeated(t):
        t._execute(t.case_unknown_id_repeated())

    def test_unknown_ids_multiple(t):
        t._execute(t.case_unknown_ids_multiple())

    def test_one_id(t):
        t._execute(t.case_one_id())

    def test_one_id_one_sub_id(t):
        t._execute(t.case_one_id_one_sub_id())

    def test_one_id_multiple_sub_ids(t):
        t._execute(t.case_one_id_multiple_sub_ids())

    def test_multiple_ids(t):
        t._execute(t.case_multiple_ids())

    def test_multiple_ids_one_sub_id_each(t):
        t._execute(t.case_multiple_ids_one_sub_id_each())

    def test_multiple_ids_multiple_sub_ids(t):
        t._execute(t.case_multiple_ids_multiple_sub_ids())

    def test_ifentry_trap(t):
        t._execute(t.case_ifentry_trap())


class TestSnmpV2VarbindHandling(_SnmpV2Base, _VarbindTests):
    def _execute(t, cases):
        try:
            pckt, handler = next(cases)
            while True:
                eventType, result = handler.decodeSnmpV2OrV3(
                    ("localhost", 162), pckt
                )
                pckt, handler = cases.send(result)
        except StopIteration:
            pass

    def test_unknown_id_single(t):
        t._execute(t.case_unknown_id_single())

    def test_unknown_id_repeated(t):
        t._execute(t.case_unknown_id_repeated())

    def test_unknown_ids_multiple(t):
        t._execute(t.case_unknown_ids_multiple())

    def test_one_id(t):
        t._execute(t.case_one_id())

    def test_one_id_one_sub_id(t):
        t._execute(t.case_one_id_one_sub_id())

    def test_one_id_multiple_sub_ids(t):
        t._execute(t.case_one_id_multiple_sub_ids())

    def test_multiple_ids(t):
        t._execute(t.case_multiple_ids())

    def test_multiple_ids_one_sub_id_each(t):
        t._execute(t.case_multiple_ids_one_sub_id_each())

    def test_multiple_ids_multiple_sub_ids(t):
        t._execute(t.case_multiple_ids_multiple_sub_ids())

    def test_ifentry_trap(t):
        t._execute(t.case_ifentry_trap())
