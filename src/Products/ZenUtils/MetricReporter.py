##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import inspect
import logging
import time

from collections import deque
from itertools import izip

import requests

from astrolabe.interval import Interval
from metrology.instruments import (
    Counter,
    Gauge,
    Histogram,
    Meter,
    Timer,
    UtilizationTimer,
)
from metrology.registry import registry
from metrology.reporter.base import Reporter
from twisted.internet import reactor, defer, task

from .controlplane import configuration as cc_config

DEFAULT_METRIC_URL = "http://localhost:22350/api/metrics/store"

log = logging.getLogger("zen.metricreporter")


class MetricReporter(Reporter):

    def __init__(self, **options):
        interval = options.get("interval", 30)
        super(MetricReporter, self).__init__(interval=interval)
        self.prefix = options.get("prefix", "")
        self.metric_destination = cc_config.consumer_url
        if not self.metric_destination:
            self.metric_destination = DEFAULT_METRIC_URL
        self.session = None
        self.tags = dict(options.get("tags", {}))
        self.tags.update(
            {
                "serviceId": cc_config.service_id,
                "instance": cc_config.instance_id,
                "hostId": cc_config.host_id,
                "tenantId": cc_config.tenant_id,
            }
        )

    def add_tags(self, tags):
        self.tags.update(tags)

    # @override
    def write(self):
        self._write()

    def _write(self):
        try:
            metrics = getMetrics(self.registry, self.tags, self.prefix)
            self.postMetrics(metrics)
        except Exception as e:
            log.exception(e)

    def postMetrics(self, metrics):
        if not self.session:
            self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.headers.update({"User-Agent": "Zenoss Service Metrics"})
        post_data = {"metrics": metrics}
        log.debug("sending metric payload: %s", post_data)
        response = self.session.post(
            self.metric_destination, data=json.dumps(post_data)
        )
        if response.status_code != 200:
            log.warning(
                "problem submitting metrics: %d, %s",
                response.status_code,
                response.text.replace("\n", "\\n"),
            )
            self.session = None
        else:
            log.debug("%d metrics posted", len(metrics))


class TwistedMetricReporter(object):
    def __init__(
        self, interval=30, metricWriter=None, tags={}, *args, **options
    ):
        super(TwistedMetricReporter, self).__init__()
        self.registry = options.get("registry", registry)
        self.prefix = options.get("prefix", "")
        self.metricWriter = metricWriter
        self.interval = interval
        self.tags = {}
        self.tags.update(tags)
        self._stopped = False
        self._loop = task.LoopingCall(self.postMetrics)

    def start(self):
        def doStart():
            self._loop.start(self.interval, now=False)

        reactor.callWhenRunning(doStart)
        reactor.addSystemEventTrigger("before", "shutdown", self.stop)

    @defer.inlineCallbacks
    def stop(self):
        if not self._stopped:
            self._stopped = True
            self._loop.stop()
            yield self.postMetrics()

    @defer.inlineCallbacks
    def postMetrics(self):
        try:
            for metric in getMetrics(self.registry, self.tags, self.prefix):
                yield self.metricWriter.write_metric(
                    metric["metric"],
                    metric["value"],
                    metric["timestamp"],
                    metric["tags"],
                )
        except Exception:
            log.exception("Error writing metrics")


class TimeOnce(object):
    """
    A context manager to time something and save tag values and
    a measurement.
    """

    def __init__(self, gauge, *args):
        self.gauge = gauge
        self.tagValues = args

    def __enter__(self):
        self.interval = Interval.now()

    def __exit__(self, *args):
        self.gauge.update(self.tagValues, self.interval.stop())


class QueueGauge(object):
    """
    This instrument contains simple point-in-time measurements like a gauge.

    Unlike a gauge, however, it:
      - can be configured to have tags whose values can vary with each
        measurement.
      - contains a queue of values with tag values, which are read only
        once each.

    Many values or none can be written to this instrument between cycles of its
    reporter, so for it many or no values will be published.

    Calling an instance returns something which should append to the instances
    queue a tuple, which should contain 1 value for each tagKey of the
    instance, followed by a measurement.
    """

    def __init__(self, *args):
        self.newContextManager = args[0] if callable(args[0]) else TimeOnce
        self.tagKeys = args if not callable(args[0]) else args[1:]
        self.queue = deque()

    def __call__(self, *args):
        if len(self.tagKeys) != len(args):
            raise RuntimeError(
                "The number of tag values provided does not match the "
                "number of configured tag keys"
            )
        return self.newContextManager(self, *args)

    def update(self, tagValues, metricValue):
        self.queue.appendleft(tagValues + (metricValue,))


def getMetrics(mRegistry, tags, prefix):
    metrics = []
    for name, metric in mRegistry:
        log.debug("metric info: %s, %s", name, metric)
        metrics.extend(getMetricData(metric, name, tags, prefix))
    return metrics


def getMetric(mRegistry, name, tags, prefix):
    if name not in mRegistry:
        log.info("%s not found in metric registry", name)
        return []
    metric = mRegistry.get(name)
    return getMetricData(metric, name, tags, prefix)


_snapshot_keys = ["median", "percentile_95th"]


def getMetricData(metric, name, tags, prefix):
    config = _getMetricConfig(metric)
    if config is None:
        log.info("could not generate a config for metric %s", name)
        return []
    fn = config["fn"]
    keys = config["keys"]
    return fn(name, metric, keys, tags, prefix, _snapshot_keys)

def _getMetricConfig(metric):
    keys = (_classname(cls) for cls in inspect.getmro(metric.__class__))
    return next(
        (_metric_configs.get(key) for key in keys if key in _metric_configs),
        None,
    )


def _log_queue_gauge(name, metric, tags, prefix):
    """
    A QueueGauge needs this unique handler because it does not contain a
    fixed number of values.
    """
    results = []

    metric_name = prefix + name if prefix else name
    ts = time.time()
    whole_metric_name = "{}.value".format(metric_name)
    try:
        while metric.queue:
            # each stat should be a tuple with 1 more member than metric.tagKeys
            stat = metric.queue.pop()
            qtags = tags.copy()
            qtags.update(izip(metric.tagKeys, stat))
            results.append(
                {
                    "metric": whole_metric_name,
                    "value": stat[-1],
                    "timestamp": ts,
                    "tags": qtags,
                }
            )
            log.debug(
                "recording metric  metric=%s value=%s",
                whole_metric_name,
                stat[-1],
            )

    except Exception as e:
        log.error(e)
    return results


def _log_metric(name, metric, keys, tags, prefix, snapshot_keys=None):
    results = []

    if snapshot_keys is None:
        snapshot_keys = []

    metric_name = prefix + name if prefix else name
    ts = time.time()
    try:
        for stat in keys:
            whole_metric_name = "%s.%s" % (metric_name, stat)
            results.append(
                {
                    "metric": whole_metric_name,
                    "value": getattr(metric, stat),
                    "timestamp": ts,
                    "tags": tags,
                }
            )
            log.debug(
                "recording metric  metric=%s value=%s",
                whole_metric_name,
                getattr(metric, stat),
            )

        if hasattr(metric, "snapshot"):
            snapshot = metric.snapshot
            for stat in snapshot_keys:
                whole_metric_name = "%s.%s" % (metric_name, stat)
                results.append(
                    {
                        "metric": whole_metric_name,
                        "value": getattr(snapshot, stat),
                        "timestamp": ts,
                        "tags": tags,
                    }
                )
                log.debug(
                    "recording metric  metric=%s value=%s",
                    whole_metric_name,
                    getattr(snapshot, stat),
                )
    except Exception as e:
        log.error(e)
    return results


def _log_without_snapshot(name, metric, keys, tags, prefix, snapshot_keys):
    return _log_metric(name, metric, keys, tags, prefix)


def _classname(obj):
    return obj.__name__ if isinstance(obj, type) else type(obj).__name__


_metric_configs = {
    _classname(Meter): {
        "fn": _log_without_snapshot,
        "keys": [
            "count",
            "one_minute_rate",
            "five_minute_rate",
            "fifteen_minute_rate",
            "mean_rate",
        ],
    },
    _classname(Gauge): {"fn": _log_without_snapshot, "keys": ["value"]},
    _classname(QueueGauge): {
        "fn": lambda name, metric, _, tags, prefix: _log_queue_gauge(
            name, metric, tags, prefix
        ),
        "keys": [],
    },
    _classname(UtilizationTimer): {
        "fn": _log_metric,
        "keys": [
            "count",
            "one_minute_rate",
            "five_minute_rate",
            "fifteen_minute_rate",
            "mean_rate",
            "min",
            "max",
            "mean",
            "stddev",
            "one_minute_utilization",
            "five_minute_utilization",
            "fifteen_minute_utilization",
            "mean_utilization",
        ],
    },
    _classname(Timer): {
        "fn": _log_metric,
        "keys": [
            "count",
            "one_minute_rate",
            "five_minute_rate",
            "fifteen_minute_rate",
            "mean_rate",
            "min",
            "max",
            "mean",
            "stddev",
        ],
    },
    _classname(Counter): {
        "fn": _log_without_snapshot,
        "keys": ["count"],
    },
    _classname(Histogram): {
        "fn": _log_metric,
        "keys": ["count", "min", "max", "mean", "stddev"],
    },
}
