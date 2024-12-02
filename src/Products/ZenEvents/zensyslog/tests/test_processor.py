##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from unittest import TestCase

import six

from Products.ZenEvents.zensyslog.processor import (
    getEventClassKeyValue,
    Parsers,
    parse_MSG,
)
from Products.ZenEvents.EventManagerBase import EventManagerBase


class TestGetEventClassKeyValue(TestCase):
    base = {"device": "localhost", "component": "component", "severity": 3}

    def setUp(t):
        logging.getLogger().setLevel(logging.CRITICAL + 10)

    def tearDown(t):
        logging.getLogger().setLevel(logging.NOTSET)

    def test_empty(t):
        empty = {}
        result = getEventClassKeyValue(empty.copy())
        t.assertIsNone(result)

    def test_eventClassKey(t):
        evt = dict(eventClassKey="akey", **t.base)
        result = getEventClassKeyValue(evt.copy())
        t.assertIsNone(result)

    def test_eventClassKey_and_ntevid(t):
        evt = dict(eventClassKey="akey", ntevid="1234", **t.base)
        result = getEventClassKeyValue(evt.copy())
        t.assertIsNone(result)

    def test_ntevid(t):
        evt = dict(ntevid="1234", **t.base)
        result = getEventClassKeyValue(evt.copy())
        t.assertEqual(result, "component_1234")

    def test_default(t):
        evt = dict(**t.base)
        result = getEventClassKeyValue(evt.copy())
        t.assertEqual(result, "component")


class TestParseMSG(TestCase):
    def setUp(t):
        logging.getLogger().setLevel(logging.CRITICAL + 10)
        t.parsers = Parsers(t.sendEvent)
        t.parsers.update(EventManagerBase.syslogParsers)

    def tearDown(t):
        del t.parsers
        logging.getLogger().setLevel(logging.NOTSET)

    def sendEvent(t, evt):
        "Fakeout sendEvent() method"
        t.sent = evt

    def test_msg_content(t):
        long_text_message = ("long text message " * 20).strip()
        msg = (
            "2016-08-08T11:07:33.660820-04:00 devname=localhost "
            "log_id=98765434 type=component {}"
        ).format(long_text_message)
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertEqual(index, -1)
        t.assertDictEqual(fields, {"summary": six.text_type(msg)})

    def testCheckFortigate(t):
        """
        Test of Fortigate syslog message parsing
        """
        key = "987654321"
        comp = "myComponent"
        msg = (
            "date=xxxx devname=blue log_id={} type={} " "blah blah blah"
        ).format(key, comp)
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("eventClassKey"), key)
        t.assertEqual(fields.get("component"), comp)
        t.assertEqual(
            fields.get("summary"),
            "devname=blue log_id=987654321 type=myComponent blah blah blah",
        )

    def testCheckCiscoPortStatus(t):
        """
        Test of Cisco port status syslog message parsing
        """
        msg = (
            "Process 10532, Nbr 192.168.10.13 on GigabitEthernet2/15 "
            "from LOADING to FULL, Loading Done"
        )
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("process_id"), "10532")
        t.assertEqual(fields.get("interface"), "GigabitEthernet2/15")
        t.assertEqual(fields.get("start_state"), "LOADING")
        t.assertEqual(fields.get("end_state"), "FULL")
        t.assertEqual(fields.get("summary"), "Loading Done")

    def testCiscoVpnConcentrator(t):
        """
        Test of Cisco VPN Concentrator syslog message parsing
        """
        msg = (
            "54884 05/25/2009 13:41:14.060 SEV=3 HTTP/42 RPT=4623 "
            "Error on socket accept."
        )
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("eventClassKey"), "HTTP/42")
        t.assertEqual(fields.get("summary"), "Error on socket accept.")

    def testCiscoStandardMessageSeverity(t):
        """
        Test that the event severity is correctly extracted from the
        Cisco standard message body
        """
        msg = (
            "2014 Jan 31 19:45:51 R2-N6K1-2010-P1 "
            "%ETH_PORT_CHANNEL-5-CREATED: port-channel1 created"
        )
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("overwriteSeverity"), "5")

    def testDellSyslog(t):
        """
        Test dell stuf
        """
        msg = (
            "1-Oct-2009 23:00:00.383809:snapshotDelete.cc:290:INFO:8.2.5:"
            "Successfully deleted snapshot "
            "'UNVSQLCLUSTERTEMPDB-2009-09-30-23:00:14.11563'."
        )
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("eventClassKey"), "8.2.5")
        t.assertEqual(
            fields.get("summary"),
            "Successfully deleted snapshot "
            "'UNVSQLCLUSTERTEMPDB-2009-09-30-23:00:14.11563'.",
        )

    def testDellSyslog2(t):
        """
        Test dell stuf
        """
        msg = (
            "2626:48:VolExec:27-Aug-2009 "
            "13:15:58.072049:VE_VolSetWorker.hh:75:WARNING:43.3.2:Volume "
            "volumeName has reached 96 percent of its reported size and "
            "is currently using 492690MB."
        )
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("eventClassKey"), "43.3.2")
        t.assertEqual(
            fields.get("summary"),
            "Volume volumeName has reached 96 percent of its reported size "
            "and is currently using 492690MB.",
        )

    def testNetAppSyslogParser(t):
        """
        Test NetApp syslog parser.
        """
        msg = (
            "[deviceName: 10/100/1000/e1a:warning]: Client 10.0.0.101 "
            "(xid 4251521131) is trying to access an unexported mount "
            "(fileid 64, snapid 0, generation 6111516 and flags 0x0 on "
            "volume 0xc97d89a [No volume name available])"
        )
        fields, index, drop = parse_MSG(msg, t.parsers)
        t.assertFalse(drop)
        t.assertTrue(index >= 0)
        t.assertEqual(fields.get("component"), "10/100/1000/e1a")
        t.assertEqual(
            fields.get("summary"),
            "Client 10.0.0.101 (xid 4251521131) is trying to access an "
            "unexported mount (fileid 64, snapid 0, generation 6111516 "
            "and flags 0x0 on volume 0xc97d89a [No volume name available])",
        )
