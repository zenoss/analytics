##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os

from zope.interface import implementer
from zope.component.interfaces import Interface, Attribute

from Products.ZenModel.BuiltInDS import BuiltInDS
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.MetricReporter import TwistedMetricReporter
from Products.ZenUtils.metricwriter import (
    AggregateMetricWriter,
    DerivativeTracker,
    FilteredMetricWriter,
    MetricWriter,
    ThresholdNotifier,
)

from .metricpublisher.publisher import RedisListPublisher, HttpPostPublisher


class IMetricManager(Interface):
    metric_writer = Attribute("metric writer instance")


@implementer(IMetricManager)
class MetricManager(object):
    """General interface for storing and reporting metrics
    metric publisher: publishes metrics to an external system (redis, http)
    metric writer: drives metric pulisher(s), calling their .put method
    metric reporter: once its .start method is called,
        periodically calls writer.write_metric, to publish stored metrics
    """

    def __init__(self, daemon_tags):
        self.daemon_tags = daemon_tags
        self._metric_writer = None
        self._metric_reporter = None

    def start(self):
        self.metricreporter.start()

    def stop(self):
        self.metricreporter.stop()

    @property
    def metricreporter(self):
        if not self._metric_reporter:
            self._metric_reporter = TwistedMetricReporter(
                metricWriter=self.metric_writer, tags=self.daemon_tags
            )

        return self._metric_reporter

    @property
    def metric_writer(self):
        if not self._metric_writer:
            self._metric_writer = _cc_metric_writer_factory()

        return self._metric_writer

    def get_rrd_stats(self, hub_config, send_event):
        rrd_stats = DaemonStats()
        thresholds = hub_config.getThresholdInstances(BuiltInDS.sourcetype)
        threshold_notifier = ThresholdNotifier(send_event, thresholds)
        derivative_tracker = DerivativeTracker()

        rrd_stats.config(
            "zenhub",
            hub_config.id,
            self.metric_writer,
            threshold_notifier,
            derivative_tracker,
        )

        return rrd_stats


def _cc_metric_writer_factory():
    metric_writer = MetricWriter(RedisListPublisher())
    cc = os.environ.get("CONTROLPLANE", "0") == "1"
    internal_url = os.environ.get("CONTROLPLANE_CONSUMER_URL", None)
    if cc and internal_url:
        username = os.environ.get("CONTROLPLANE_CONSUMER_USERNAME", "")
        password = os.environ.get("CONTROLPLANE_CONSUMER_PASSWORD", "")
        _publisher = HttpPostPublisher(username, password, internal_url)
        internal_metric_writer = FilteredMetricWriter(
            _publisher, _internal_metric_filter
        )
        metric_writer = AggregateMetricWriter(
            [metric_writer, internal_metric_writer]
        )
    return metric_writer


def _internal_metric_filter(metric, value, timestamp, tags):
    return tags and tags.get("internal", False)
