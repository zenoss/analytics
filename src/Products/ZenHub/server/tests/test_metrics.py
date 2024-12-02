##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from collections import defaultdict
from unittest import TestCase
from mock import call, Mock, patch

from ..config import legacy_metric_priority_map
from ..metrics import (
    _CallStats,
    _CountKey,
    _legacy_metric_worklist_total,
    decrementLegacyMetricCounters,
    handleServiceCallCompleted,
    handleServiceCallReceived,
    handleServiceCallStarted,
    IHubServerConfig,
    IMetricManager,
    incrementLegacyMetricCounters,
    markEventsSent,
    register_legacy_worklist_metrics,
    ServiceCallPriority,
    ServiceCallCompleted,
    ServiceCallReceived,
    ServiceCallStarted,
    WorkListGauge,
)

PATH = {"src": "Products.ZenHub.server.metrics"}


class WorkListGaugeTest(TestCase):
    """Test for the WorkListGauge class."""

    def setUp(t):
        t.counters = defaultdict(lambda: 0)
        t.key = "key"
        t.gauge = WorkListGauge(t.counters, t.key)

    def test_initial_value(t):
        t.assertEqual(0, t.gauge.value)

    def test_modified_value(t):
        t.counters[t.key] = 5
        t.assertEqual(5, t.gauge.value)

    def test_multiple_gauges(t):
        key2 = "key2"
        gauge2 = WorkListGauge(t.counters, key2)

        t.counters[t.key] = 5
        t.counters[key2] = 3

        t.assertEqual(5, t.gauge.value)
        t.assertEqual(3, gauge2.value)


class LegacyMetricsTest(TestCase):
    """Test for legacy metrics."""

    @patch("{src}.registry".format(**PATH), autospec=True)
    @patch("{src}.Metrology".format(**PATH), autospec=True)
    @patch("{src}.getUtility".format(**PATH), autospec=True)
    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    @patch("{src}.WorkListGauge".format(**PATH))
    def test_metrology_registration(
        self,
        _WorkListGauge,
        _counters,
        _getUtility,
        _Metrology,
        _registry,
    ):
        config = Mock()
        config.legacy_metric_priority_map = legacy_metric_priority_map
        _getUtility.return_value = config

        metrics = {}
        _registry.metrics = metrics

        expected_worklist_gauge_calls = [
            call(_counters, ServiceCallPriority.EVENTS),
            call(_counters, ServiceCallPriority.MODELING),
            call(_counters, ServiceCallPriority.SINGLE_MODELING),
            call(_counters, ServiceCallPriority.OTHER),
            call(_counters, _legacy_metric_worklist_total.name),
        ]
        expected_worklist_gauge_call_count = len(expected_worklist_gauge_calls)

        wgauge = _WorkListGauge.return_value
        expected_metrology_gauge_calls = [
            call("zenhub.eventWorkList", wgauge),
            call("zenhub.admWorkList", wgauge),
            call("zenhub.otherWorkList", wgauge),
            call("zenhub.singleADMWorkList", wgauge),
            call(_legacy_metric_worklist_total.metric, wgauge),
        ]
        expected_metrology_gauge_call_count = len(
            expected_metrology_gauge_calls,
        )

        expected_counter_contents = {
            ServiceCallPriority.EVENTS: 0,
            ServiceCallPriority.MODELING: 0,
            ServiceCallPriority.OTHER: 0,
            ServiceCallPriority.SINGLE_MODELING: 0,
            _legacy_metric_worklist_total.name: 0,
        }

        register_legacy_worklist_metrics()

        _getUtility.assert_called_once_with(IHubServerConfig)

        self.assertEqual(
            expected_worklist_gauge_call_count,
            _WorkListGauge.call_count,
        )
        _WorkListGauge.assert_has_calls(
            expected_worklist_gauge_calls,
            any_order=True,
        )

        self.assertEqual(
            expected_metrology_gauge_call_count,
            _Metrology.gauge.call_count,
        )
        _Metrology.gauge.assert_has_calls(
            expected_metrology_gauge_calls,
            any_order=True,
        )

        self.assertDictEqual(expected_counter_contents, _counters)

        _Metrology.meter.assert_called_once_with("zenhub.eventsSent")

    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_incrementCounters(self, _counters):
        event = Mock(spec=["priority"])
        _counters[event.priority] = 0
        _counters["total"] = 0

        incrementLegacyMetricCounters(event)

        self.assertEqual(1, _counters[event.priority])
        self.assertEqual(1, _counters["total"])
        self.assertListEqual(
            sorted([event.priority, "total"]),
            sorted(_counters.keys()),
        )

    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_skip_decrement(self, _counters):
        event = Mock(spec=["retry"])
        event.retry = object()

        decrementLegacyMetricCounters(event)

        self.assertDictEqual({}, _counters)

    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_decrementCounters(self, _counters):
        event = Mock(spec=["priority", "retry"])
        event.retry = None
        _counters[event.priority] = 1
        _counters["total"] = 1

        decrementLegacyMetricCounters(event)

        self.assertEqual(0, _counters[event.priority])
        self.assertEqual(0, _counters["total"])
        self.assertListEqual(
            sorted([event.priority, "total"]),
            sorted(_counters.keys()),
        )

    @patch("{src}.log".format(**PATH), autospec=True)
    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_decrementCounters_to_negative(self, _counters, _log):
        event = Mock(spec=["priority", "retry"])
        event.retry = None
        _counters[event.priority] = 0
        _counters["total"] = 0

        decrementLegacyMetricCounters(event)

        self.assertEqual(2, _log.warn.call_count)
        self.assertEqual(-1, _counters[event.priority])
        self.assertEqual(-1, _counters["total"])
        self.assertListEqual(
            sorted([event.priority, "total"]),
            sorted(_counters.keys()),
        )

    @patch("{src}._legacy_events_meter".format(**PATH), spec=["mark"])
    def test_skip_markEventsSent(self, _meter):
        event = Mock(spec=["retry"])
        event.retry = object()

        markEventsSent(event)

        self.assertEqual(0, _meter.mark.call_count)

    @patch("{src}._legacy_events_meter".format(**PATH), spec=["mark"])
    def test_sendEvent(self, _meter):
        event = Mock(spec=["method", "retry"])
        event.retry = None
        event.method = "sendEvent"

        markEventsSent(event)

        _meter.mark.assert_called_once_with()

    @patch("{src}._legacy_events_meter".format(**PATH), spec=["mark"])
    def test_sendEvents(self, _meter):
        event = Mock(spec=["method", "retry", "args"])
        event.retry = None
        event.method = "sendEvents"
        event.args = [0, 1]

        markEventsSent(event)

        _meter.mark.assert_called_once_with(len(event.args))


class ServiceCallMetricsTest(TestCase):
    """Test the ServiceCall metrics handling."""

    def setUp(self):
        _patchables = (
            ("_task_stats", defaultdict(_CallStats)),
            ("_servicecall_count", defaultdict(int)),
            ("_servicecall_wip", defaultdict(int)),
            ("getUtility", Mock(spec=[])),
        )
        for name, value in _patchables:
            patcher = patch(
                "{src}.{name}".format(src=PATH["src"], name=name),
                new=value,
            )
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_handleServiceCallReceived(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallReceived)
        event.timestamp = 100.0
        key = _CountKey(event)

        handleServiceCallReceived(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(event.timestamp, self._task_stats[event.id].received)
        self.assertEqual(0.0, self._task_stats[event.id].started)
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, self._servicecall_count[key])
        self.assertEqual(0, len(self._servicecall_wip))
        writer.write_metric.assert_called_once_with(
            "zenhub.servicecall.count",
            1,
            event.timestamp * 1000,
            {
                "queue": event.queue,
                "priority": event.priority.name,
                "service": event.service,
                "method": event.method,
            },
        )

    def test_handleServiceCallStarted(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallStarted)
        event.timestamp = 100.0
        key = _CountKey(event)

        handleServiceCallStarted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0.0, self._task_stats[event.id].received)
        self.assertEqual(event.timestamp, self._task_stats[event.id].started)
        self.assertEqual(0, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(1, self._servicecall_wip[key])
        writer.write_metric.assert_called_once_with(
            "zenhub.servicecall.wip",
            1,
            event.timestamp * 1000,
            {
                "queue": event.queue,
                "priority": event.priority.name,
                "service": event.service,
                "method": event.method,
            },
        )

    def test_handleServiceCallCompleted_success(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = None
        event.retry = None
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0
        self._servicecall_count[key] += 1
        self._servicecall_wip[key] += 1

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(0, self._servicecall_count[key])
        self.assertEqual(0, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls(
            (
                call(
                    "zenhub.servicecall.wip",
                    0,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.cycletime",
                    10000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                        "status": "success",
                    },
                ),
                call(
                    "zenhub.servicecall.count",
                    0,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.leadtime",
                    60000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
            ),
            any_order=True,
        )

    def test_handleServiceCallCompleted_retry(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = None
        event.retry = object()
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0
        self._servicecall_count[key] += 1
        self._servicecall_wip[key] += 1

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(1, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(1, self._servicecall_count[key])
        self.assertEqual(0, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls(
            (
                call(
                    "zenhub.servicecall.wip",
                    0,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.cycletime",
                    10000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                        "status": "retry",
                    },
                ),
            ),
            any_order=True,
        )

    def test_handleServiceCallCompleted_failure(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = object()
        event.retry = None
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0
        self._servicecall_count[key] += 1
        self._servicecall_wip[key] += 1

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(0, self._servicecall_count[key])
        self.assertEqual(0, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls(
            (
                call(
                    "zenhub.servicecall.wip",
                    0,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.cycletime",
                    10000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                        "status": "failure",
                    },
                ),
                call(
                    "zenhub.servicecall.count",
                    0,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.leadtime",
                    60000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
            ),
            any_order=True,
        )

    @patch("{src}.log".format(**PATH), autospec=True)
    def test_negative_values(self, _log):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = None
        event.retry = None
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(-1, self._servicecall_count[key])
        self.assertEqual(-1, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls(
            (
                call(
                    "zenhub.servicecall.wip",
                    -1,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.cycletime",
                    10000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                        "status": "success",
                    },
                ),
                call(
                    "zenhub.servicecall.count",
                    -1,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
                call(
                    "zenhub.servicecall.leadtime",
                    60000,
                    160000,
                    {
                        "queue": event.queue,
                        "priority": event.priority.name,
                        "service": event.service,
                        "method": event.method,
                    },
                ),
            ),
            any_order=True,
        )
        self.assertEqual(2, _log.warn.call_count)
