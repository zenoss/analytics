##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import Mock, patch, sentinel

from Products.ZenHub.metricmanager import (
    MetricManager,
    _cc_metric_writer_factory,
    _internal_metric_filter,
)


PATH = {"src": "Products.ZenHub.metricmanager"}


class MetricManagerTest(TestCase):
    def setUp(t):
        t.tmr_patcher = patch(
            "{src}.TwistedMetricReporter".format(**PATH),
            autospec=True,
        )
        t.TwistedMetricReporter = t.tmr_patcher.start()
        t.addCleanup(t.tmr_patcher.stop)

        t.daemon_tags = {
            "zenoss_daemon": "zenhub",
            "zenoss_monitor": "localhost",
            "internal": True,
        }

        t.mm = MetricManager(t.daemon_tags)

    def test___init__(t):
        t.assertEqual(t.mm.daemon_tags, t.daemon_tags)

    def test_start(t):
        t.mm.start()
        t.mm.metricreporter.start.assert_called_with()

    def test_stop(t):
        t.mm.stop()
        t.mm.metricreporter.stop.assert_called_with()

    def test_metric_reporter(t):
        t.assertEqual(
            t.mm.metricreporter, t.TwistedMetricReporter.return_value
        )
        t.TwistedMetricReporter.assert_called_with(
            metricWriter=t.mm.metric_writer, tags=t.mm.daemon_tags
        )

    @patch("{src}._cc_metric_writer_factory".format(**PATH), autospec=True)
    def test_metric_writer(t, _cc_metric_writer_factory):
        ret = t.mm.metric_writer
        t.assertEqual(ret, _cc_metric_writer_factory.return_value)

    @patch("{src}.BuiltInDS".format(**PATH), autospec=True)
    @patch("{src}.DerivativeTracker".format(**PATH), autospec=True)
    @patch("{src}.ThresholdNotifier".format(**PATH), autospec=True)
    @patch("{src}.DaemonStats".format(**PATH), autospec=True)
    def test_get_rrd_stats(
        t, DaemonStats, ThresholdNotifier, DerivativeTracker, BuiltInDS
    ):
        hub_config = Mock(
            name="hub_config", spec_set=["getThresholdInstances", "id"]
        )
        send_event = sentinel.send_event_function

        ret = t.mm.get_rrd_stats(hub_config, send_event)

        rrd_stats = DaemonStats.return_value
        thresholds = hub_config.getThresholdInstances.return_value
        threshold_notifier = ThresholdNotifier.return_value
        derivative_tracker = DerivativeTracker.return_value

        hub_config.getThresholdInstances.assert_called_with(
            BuiltInDS.sourcetype
        )
        ThresholdNotifier.assert_called_with(send_event, thresholds)

        rrd_stats.config.assert_called_with(
            "zenhub",
            hub_config.id,
            t.mm.metric_writer,
            threshold_notifier,
            derivative_tracker,
        )

        t.assertEqual(ret, DaemonStats.return_value)


class MetricManagerModuleTest(TestCase):
    @patch("{src}.AggregateMetricWriter".format(**PATH), autospec=True)
    @patch("{src}.FilteredMetricWriter".format(**PATH), autospec=True)
    @patch("{src}.HttpPostPublisher".format(**PATH), autospec=True)
    @patch("{src}.os".format(**PATH), autospec=True)
    @patch("{src}.RedisListPublisher".format(**PATH), autospec=True)
    @patch("{src}.MetricWriter".format(**PATH), autospec=True)
    def test__cc_metric_writer_factory(
        t,
        MetricWriter,
        RedisListPublisher,
        os,
        HttpPostPublisher,
        FilteredMetricWriter,
        AggregateMetricWriter,
    ):
        usr, pas = "consumer_username", "consumer_password"
        internal_url = "consumer_url"
        os.environ = {
            "CONTROLPLANE": "1",
            "CONTROLPLANE_CONSUMER_URL": internal_url,
            "CONTROLPLANE_CONSUMER_USERNAME": usr,
            "CONTROLPLANE_CONSUMER_PASSWORD": pas,
        }

        metric_writer = _cc_metric_writer_factory()

        MetricWriter.assert_called_with(RedisListPublisher.return_value)
        HttpPostPublisher.assert_called_with(usr, pas, internal_url)
        FilteredMetricWriter.assert_called_with(
            HttpPostPublisher.return_value, _internal_metric_filter
        )
        AggregateMetricWriter.assert_called_with(
            [MetricWriter.return_value, FilteredMetricWriter.return_value]
        )
        t.assertEqual(metric_writer, AggregateMetricWriter.return_value)

    def test_internal_metric_filter(t):
        tags = {"t1": True, "internal": True}
        ret = _internal_metric_filter(
            sentinel.metric, sentinel.value, sentinel.timestamp, tags
        )
        t.assertEqual(ret, True)

    def test_internal_metric_filter_False(t):
        tags = {"t1": True, "not internal": True}
        ret = _internal_metric_filter(
            sentinel.metric, sentinel.value, sentinel.timestamp, tags
        )
        t.assertEqual(ret, False)
