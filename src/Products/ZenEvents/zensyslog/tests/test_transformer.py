##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import collections

from unittest import TestCase
from mock import Mock

from Products.ZenHub.interfaces import TRANSFORM_CONTINUE, TRANSFORM_DROP

from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenEvents.zensyslog.transformer import (
    FilterRules,
    SyslogMsgFilter,
)


class SyslogMsgFilterTest(TestCase):
    def setUp(t):
        logging.getLogger().setLevel(logging.CRITICAL + 10)

    def tearDown(t):
        logging.getLogger().setLevel(logging.NOTSET)

    def testDefaultFilterRules(self):
        app = Mock()
        rules = FilterRules(app)
        rules.update(EventManagerBase.syslogMsgEvtFieldFilterRules)
        self.assertEquals(app.sendEvent.called, False)

    def testBadFilter(self):
        filterCfg = {"eventClassKey": ["(BadBad"]}
        app = Mock()
        rules = FilterRules(app)
        rules.update(filterCfg)
        self.assertEqual(len(rules), 0)
        self.assertTrue(app.sendEvent.called)
        self.assertEquals(app.sendEvent.call_count, 1)
        evtFields = app.sendEvent.mock_calls[0][1][0]
        self.assertEquals(
            evtFields["message"],
            "Syslog Message Filter configuration for the 'eventClassKey' "
            "event field could not compile rule #0 with the expression "
            "of '(BadBad'. Error error('unbalanced parenthesis',)",
        )

    def testSyslogMsgFilterMatch(self):
        filterCfg = {"eventClassKey": ["MARK"]}
        event = {
            "severity": 4,
            "eventClassKey": "MARK",
            "component": "zensyslog",
            "summary": "test message",
            "eventKey": "SyslogMessageFilter.eventClassKey.0",
            "device": "127.0.0.1",
            "eventClass": "/App/Zenoss",
            "message": "test test 123",
        }
        app = Mock()
        rules = FilterRules(app)
        counters = collections.Counter()
        counters["eventCount"] = 0
        counters["eventFilterDroppedCount"] = 0
        transformer = SyslogMsgFilter(rules, counters)
        rules.update(filterCfg)
        self.assertFalse(app.sendEvent.called)
        result = transformer.transform(event)
        self.assertEquals(result, TRANSFORM_DROP)
        event["eventClassKey"] = "NotMark"
        result = transformer.transform(event)
        self.assertEquals(result, TRANSFORM_CONTINUE)
