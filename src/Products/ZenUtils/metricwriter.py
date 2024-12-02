##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
import types
from twisted.internet import defer
from Products.ZenRRD.Thresholds import Thresholds

log = logging.getLogger("zen.MetricWriter")


class MetricWriter(object):
    def __init__(self, publisher):
        self._publisher = publisher
        self._datapoints = 0

    def write_metric(self, metric, value, timestamp, tags):
        """
        Wraps calls to a deferred publisher

        @param metric:
        @param value:
        @param timestamp:
        @param tags:
        @return deferred: metric was published or queued
        """
        try:
            if tags and "mtrace" in tags.keys():
                log.info(
                    "mtrace: publishing metric %s %s %s %s",
                    metric,
                    value,
                    timestamp,
                    tags,
                )
            log.debug(
                "publishing metric %s %s %s %s", metric, value, timestamp, tags
            )
            val = defer.maybeDeferred(
                self._publisher.put, metric, value, timestamp, tags
            )
            self._datapoints += 1
            return val
        except Exception as x:
            log.exception(x)

    @property
    def dataPoints(self):
        """
        The number of datapoints that have been published
        @return: int
        """
        return self._datapoints


class FilteredMetricWriter(object):
    def __init__(self, publisher, test_filter):
        self._datapoints = 0
        self._test_filter = test_filter
        self._publisher = publisher

    def write_metric(self, metric, value, timestamp, tags):
        """
        Wraps calls to a deferred publisher when the test_filter passes

        @param metric:
        @param value:
        @param timestamp:
        @param tags:
        @return deferred: metric was published or queued
        """
        try:
            if self._test_filter(metric, value, timestamp, tags):
                if tags and "mtrace" in tags.keys():
                    log.info(
                        "mtrace: publishing metric %s %s %s %s",
                        metric,
                        value,
                        timestamp,
                        tags,
                    )
                log.debug(
                    "publishing metric %s %s %s %s",
                    metric,
                    value,
                    timestamp,
                    tags,
                )
                val = defer.maybeDeferred(
                    self._publisher.put, metric, value, timestamp, tags
                )
                self._datapoints += 1
                return val
        except Exception as x:
            log.exception(x)

    @property
    def dataPoints(self):
        """
        The number of datapoints that have been published
        @return: int
        """
        return self._datapoints


class AggregateMetricWriter(object):
    def __init__(self, writers):
        self._datapoints = 0
        self._writers = writers

    def write_metric(self, metric, value, timestamp, tags):
        """
        Writes metrics to multiple metric writers

        @param metric:
        @param value:
        @param timestamp:
        @param tags:
        @return deferred: metric was published or queued
        """
        dList = []
        for writer in self._writers:
            try:
                dList.append(
                    defer.maybeDeferred(
                        writer.write_metric, metric, value, timestamp, tags
                    )
                )
            except Exception as x:
                log.exception(x)
        self._datapoints += 1
        return defer.DeferredList(dList)

    @property
    def dataPoints(self):
        """
        The number of datapoints that have been published
        @return: int
        """
        return self._datapoints


class DerivativeTracker(object):
    def __init__(self):
        self._timed_metric_cache = {}

    def derivative(self, name, timed_metric, min="U", max="U"):
        """
        Tracks a metric value over time and returns deltas

        @param name: used to track a specific metric over time
        @param timed_metric: tuple of (value, timestamp)
        @param min: derivative will be None if below this value
        @param max: derivative will be None if above this value
        @return: change from previous value if a previous value exists
        """
        last_timed_metric = self._timed_metric_cache.get(name)

        # Store timed_metric for comparison next time.
        self._timed_metric_cache[name] = timed_metric

        if last_timed_metric:
            if timed_metric[1] == last_timed_metric[1]:
                # Regardless of v0 and v1, two samples at the same time results
                # in an infinity/nan rate.
                return None
            else:
                delta = float(timed_metric[0] - last_timed_metric[0]) / float(
                    timed_metric[1] - last_timed_metric[1]
                )

                # Get min/max into a usable float or None state.
                min, max = map(constraint_value, (min, max))

                # Derivatives below min are invalid and result in None.
                if min is not None and delta < min:
                    return None

                # Derivatives above max are invalid and result in None.
                if max is not None and delta > max:
                    return None

                return delta

        # None would be returned, but being explicit about it in this case.
        return None


def constraint_value(value):
    """Return float or None from raw rrdmin/rrdmax value.

    >>> constraint_value('U')
    >>> constraint_value('')
    >>> constraint_value('no thanks')
    >>> constraint_value(1)
    1.0
    >>> constraint_value(1.1)
    1.1
    >>> constraint_value('1')
    1.0
    >>> constraint_value('1.1')
    1.1

    """
    if isinstance(value, float):
        return value
    elif isinstance(value, int):
        return float(value)
    elif isinstance(value, types.StringTypes):
        if value in ("U", ""):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class ThresholdNotifier(object):
    """
    Encapsulates the logic necessary to evaluate a datapoint value
    against thresholds and send any events that are generated from
    threshold evaluation. Used by CollectorDaemon and DaemonStats.
    """

    def __init__(self, send_callback, thresholds):
        self._send_callback = send_callback
        if isinstance(thresholds, list):
            self._thresholds = Thresholds()
            self._thresholds.updateList(thresholds)
        elif isinstance(thresholds, Thresholds):
            self._thresholds = thresholds
        else:
            self._thresholds = Thresholds()

    def updateThresholds(self, thresholds):
        self._thresholds.updateList(thresholds)

    @defer.inlineCallbacks
    def notify(
        self,
        context_uuid,
        context_id,
        metric,
        timestamp,
        value,
        thresh_event_data=None,
    ):
        """
        Check the specified value against thresholds and send any generated
        events

        @param context_uuid: context name used to check thresholds
        @param context_id: can be used for event key prefix
        @param metric: name of the metric
        @param timestamp: timestamp for the value
        @param value: the value to check
        @param thresh_event_data: additional data to send with any events
        @return:
        """
        if self._thresholds and value is not None:
            thresh_event_data = thresh_event_data or {}
            if "eventKey" in thresh_event_data:
                eventKeyPrefix = [thresh_event_data["eventKey"]]
            else:
                eventKeyPrefix = [metric]
            for ev in self._thresholds.check(
                context_uuid, metric, timestamp, value
            ):
                parts = eventKeyPrefix[:]
                if "eventKey" in ev:
                    parts.append(ev["eventKey"])
                ev["eventKey"] = "|".join(parts)
                # add any additional values for this threshold
                # (only update if key is not in event, or if
                # the event's value is blank or None)
                for key, value in thresh_event_data.items():
                    if ev.get(key, None) in ("", None):
                        ev[key] = value
                if ev.get("component", None):
                    ev["component_guid"] = context_uuid
                yield defer.maybeDeferred(self._send_callback, ev)
