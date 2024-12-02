##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time

from collections import defaultdict
from datetime import datetime, timedelta
from metrology import Metrology
from metrology.instruments import Gauge
from metrology.registry import registry
from zope.component import adapter, getUtility, provideHandler

from ..metricmanager import IMetricManager
from .events import (
    ServiceCallReceived,
    ServiceCallStarted,
    ServiceCallCompleted,
)
from .interface import IHubServerConfig
from .priority import ServiceCallPriority
from .utils import getLogger

log = getLogger("metrics")

_legacy_metric_worklist_total = type(
    "WorkListTotalNames",
    (object,),
    {"metric": "zenhub.workList", "name": "total"},
)()

# Dict[Union[str, ServiceCallPriority], int]
_legacy_worklist_counters = defaultdict(lambda: 0)

_legacy_events_meter = None


class WorkListGauge(Gauge):
    """Wraps a Metrology Gauge to sample the size of zenhub worklists."""

    def __init__(self, counters, key):
        self.__counters = counters
        self.__key = key

    @property
    def value(self):
        return self.__counters[self.__key]


def register_legacy_worklist_metrics():
    """Create the Metrology counters for tracking worklist statistics."""
    config = getUtility(IHubServerConfig)
    global _legacy_worklist_counters

    for metricName, priorityName in config.legacy_metric_priority_map.items():
        gauge = registry.metrics.get(metricName)
        priority = ServiceCallPriority[priorityName]
        if not gauge:
            gauge = WorkListGauge(_legacy_worklist_counters, priority)
            Metrology.gauge(metricName, gauge)
        _legacy_worklist_counters[priority] = 0

    gauge = registry.metrics.get(_legacy_metric_worklist_total.metric)
    if not gauge:
        gauge = WorkListGauge(
            _legacy_worklist_counters,
            _legacy_metric_worklist_total.name,
        )
        Metrology.gauge(_legacy_metric_worklist_total.metric, gauge)
    _legacy_worklist_counters["total"] = 0

    global _legacy_events_meter
    _legacy_events_meter = Metrology.meter("zenhub.eventsSent")


@adapter(ServiceCallReceived)
def incrementLegacyMetricCounters(event):
    """Update the legacy metric counters."""
    global _legacy_worklist_counters
    _legacy_worklist_counters[event.priority] += 1
    _legacy_worklist_counters["total"] += 1


@adapter(ServiceCallCompleted)
def decrementLegacyMetricCounters(event):
    """Update the legacy worklist counters."""
    # When 'retry' is not None, the service call has not left the worklist.
    if event.retry is not None:
        return
    global _legacy_worklist_counters
    for key in (event.priority, "total"):
        _legacy_worklist_counters[key] -= 1
        # If the count falls below zero,
        # there's a bug and should be logged.
        if _legacy_worklist_counters[key] < 0:
            log.warn(
                "Counter is negative worklist=%s value=%s",
                key,
                _legacy_worklist_counters[key],
            )


@adapter(ServiceCallCompleted)
def markEventsSent(event):
    """Update the legacy eventsSent metric."""
    if event.retry is not None:
        return
    global _legacy_events_meter
    if event.method == "sendEvent":
        _legacy_events_meter.mark()
    elif event.method == "sendEvents":
        _legacy_events_meter.mark(len(event.args))


# Metrics
# -------
# zenhub.servicecall.count  -- Count of current service calls
#   + queue
#   + priority
#   + method
#   + service
# zenhub.servicecall.wip  -- Count of service calls currently executing
#   + queue
#   + priority
#   + method
#   + service
# zenhub.servicecall.leadtime  -- Amount of time call existed
#   + queue
#   + priority
#   + method
#   + service
# zenhub.servicecall.cycletime  -- How long call took to execute
#   + queue
#   + priority
#   + method
#   + service
#   + status  ["success", "failure", "retry"]


def _toMillis(seconds):
    return int(seconds * 1000)


class _CallStats(object):

    __slots__ = ("received", "started")

    def __init__(self):
        self.received = 0.0
        self.started = 0.0


# Track the arrival and start times for individual service calls
# Key: The service call's unique ID
# Value: _CallStats instance
# Dict[str, _CallStats]
_task_stats = defaultdict(_CallStats)

# Count of current service calls
# Key: _CountKey instance
# Value: int
# Dict[_CountKey, int]
_servicecall_count = defaultdict(int)

# Count of service calls currently executing
# Key: _CountKey instance
# Value: int
# Dict[_CountKey, int]
_servicecall_wip = defaultdict(int)


class _CountKey(object):
    """Uniquely identify a service, method, priority, queue combination."""

    __slots__ = ("_hash",)

    def __init__(self, event):
        self._hash = hash(
            (
                event.service,
                event.method,
                event.priority,
                event.queue,
            )
        )

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, _CountKey):
            return NotImplemented
        return self._hash == other._hash


def _make_tags(event):
    return {
        "queue": event.queue,
        "priority": event.priority.name,
        "service": event.service,
        "method": event.method,
    }


def _get_cycle_status(event):
    if event.error:
        return "failure"
    elif event.retry:
        return "retry"
    else:
        return "success"


@adapter(ServiceCallReceived)
def handleServiceCallReceived(event):
    """Update statistics and metrics using the ServiceCallReceived event."""
    # Record when the task was received
    _task_stats[event.id].received = event.timestamp

    # Increment the count
    writer = getUtility(IMetricManager).metric_writer
    key = _CountKey(event)
    _servicecall_count[key] += 1
    writer.write_metric(
        "zenhub.servicecall.count",
        _servicecall_count[key],
        _toMillis(event.timestamp),
        _make_tags(event),
    )


@adapter(ServiceCallStarted)
def handleServiceCallStarted(event):
    """Update statistics and metrics using ServiceCallStarted events."""
    # Record when the task was started
    _task_stats[event.id].started = event.timestamp

    # Update the work-in-progress (wip) metric;
    # Work-in-progress is the count of service calls currently executing.
    writer = getUtility(IMetricManager).metric_writer
    key = _CountKey(event)
    _servicecall_wip[key] += 1
    writer.write_metric(
        "zenhub.servicecall.wip",
        _servicecall_wip[key],
        _toMillis(event.timestamp),
        _make_tags(event),
    )


@adapter(ServiceCallCompleted)
def handleServiceCallCompleted(event):
    """Update statistics and metrics using the ServiceCallReceived event."""
    writer = getUtility(IMetricManager).metric_writer
    milliseconds = _toMillis(event.timestamp)
    key = _CountKey(event)
    tags = _make_tags(event)

    # Update the cycletime metric;
    # Cycletime is the duration of a servicecall.
    started_tm = _task_stats[event.id].started
    duration = _toMillis(event.timestamp - started_tm)
    cycletags = dict(tags)
    cycletags["status"] = _get_cycle_status(event)
    writer.write_metric(
        "zenhub.servicecall.cycletime",
        duration,
        milliseconds,
        cycletags,
    )

    # Update the work-in-progress (wip) metric;
    # Work-in-progress is the count of service calls currently executing.
    _servicecall_wip[key] -= 1
    if _servicecall_wip[key] < 0:
        log.warn(
            "Invalid value "
            "value=%s metric=%s service=%s method=%s priority=%s queue=%s",
            _servicecall_wip[key],
            "zenhub.servicecall.wip",
            event.service,
            event.method,
            event.priority.name,
            event.queue,
        )
    writer.write_metric(
        "zenhub.servicecall.wip",
        _servicecall_wip[key],
        milliseconds,
        tags,
    )

    # When event.retry is None, the service call is not re-executed
    # and the leadtime and count metrics can be updated.
    if event.retry is None:
        # Decrement the count because the call has left the queue.
        _servicecall_count[key] -= 1
        if _servicecall_count[key] < 0:
            log.warn(
                "Invalid value "
                "value=%s metric=%s service=%s method=%s priority=%s queue=%s",
                _servicecall_count[key],
                "zenhub.servicecall.count",
                event.service,
                event.method,
                event.priority.name,
                event.queue,
            )
        writer.write_metric(
            "zenhub.servicecall.count",
            _servicecall_count[key],
            milliseconds,
            tags,
        )
        # Update the leadtime metric;
        # Leadtime is the total time the call existed, including the time
        # it spent waiting to be executed and the time spent executing the
        # call (or multiple executions if the call was retried).
        received_tm = _task_stats[event.id].received
        leadtime = _toMillis(event.timestamp - received_tm)
        writer.write_metric(
            "zenhub.servicecall.leadtime",
            leadtime,
            milliseconds,
            tags,
        )
        # Remove the completed call from the task_* maps.
        del _task_stats[event.id]


def make_status_reporter():
    """Return an instance of ZenHubStatusReporter."""
    monitor = StatsMonitor()
    return ZenHubStatusReporter(monitor)


class ZenHubStatusReporter(object):
    """Status Reporter for ZenHub."""

    def __init__(self, stats):
        """Initialize an instance of ZenHubStatusReporter.

        :param stats: Worker and Task statistics tracker.
        :type stats: StatsMonitor
        """
        self.__stats = stats
        self.__heading_priority_seq = (
            ("Events", ServiceCallPriority.EVENTS),
            ("Other", ServiceCallPriority.OTHER),
            ("ApplyDataMaps (batch)", ServiceCallPriority.MODELING),
            ("ApplyDataMaps (single)", ServiceCallPriority.SINGLE_MODELING),
        )

    def getReport(self):
        """Return a report on the services."""
        now = time.time()

        lines = ["Worklist Stats:"]
        lines.extend(
            "   {:<22}: {}".format(
                priority,
                _legacy_worklist_counters[key],
            )
            for priority, key in self.__heading_priority_seq
        )
        lines.extend(
            [
                "   {:<22}: {}".format(
                    "Total",
                    _legacy_worklist_counters["total"],
                ),
                "",
                "Service Call Statistics:",
                "   {:<32} {:>8} {:>12} {} ".format(
                    "method",
                    "count",
                    "running_total",
                    "last_called_time",
                ),
            ]
        )

        tasks = self.__stats.tasks
        statline = " - {:<32} {:>8} {:>12}  {:%Y-%m-%d %H:%M:%S}"
        sorted_by_running_total = sorted(
            tasks.iteritems(),
            key=lambda e: -(e[1].running_total),
        )
        lines.extend(
            statline.format(
                method,
                stats.count,
                timedelta(seconds=round(stats.running_total)),
                datetime.fromtimestamp(stats.last_completed),
            )
            for method, stats in sorted_by_running_total
        )

        workers = self.__stats.workers
        lines.extend(
            [
                "",
                "Worker Statistics:",
            ]
        )
        nostatsFmt = "    {:>2}:Idle [] No tasks run"
        statsFmt = "    {:>2}:{} [{}  elapsed: {}] idle: {}"
        for workerId, stats in sorted(workers.iteritems()):
            if not stats or not (stats.current_task or stats.last_task):
                lines.append(nostatsFmt.format(workerId))
                continue
            if stats.current_task:
                ct = stats.current_task
                lt = stats.last_task
                desc = ct.description
                elapsed = timedelta(seconds=round(now - ct.started))
                if lt:
                    idle = timedelta(seconds=round(ct.started - lt.completed))
                else:
                    idle = "n/a"
            else:
                lt = stats.last_task
                desc = lt.description
                elapsed = timedelta(seconds=round(lt.completed - lt.started))
                idle = timedelta(seconds=round(now - lt.completed))
            lines.append(
                statsFmt.format(
                    workerId,
                    stats.status,
                    desc,
                    elapsed,
                    idle,
                )
            )
        return "\n".join(lines)


class StatsMonitor(object):
    """Records statistics on zenhubworker activity."""

    def __init__(self):
        self.__counters = defaultdict(lambda: 0)
        self.__worker_stats = defaultdict(_WorkerStats)
        self.__task_stats = defaultdict(_TaskStats)
        provideHandler(self._updateWorkerItems)
        provideHandler(self._incrementWorkListCount)
        provideHandler(self._decrementWorkListCount)
        provideHandler(self._handleServiceCallStarted)
        provideHandler(self._handleServiceCallCompleted)

    @property
    def counters(self):
        return self.__counters

    @property
    def workers(self):
        return self.__worker_stats

    @property
    def tasks(self):
        return self.__task_stats

    def update_rrd_stats(self, rrdstats, service_manager):
        totalTime = sum(s.callTime for s in service_manager.services.values())
        rrdstats.gauge("services", len(service_manager.services))
        rrdstats.counter("totalCallTime", totalTime)

        instruments = dict(registry)
        workListGauge = instruments.get(_legacy_metric_worklist_total.metric)
        if workListGauge is not None:
            rrdstats.gauge("workListLength", workListGauge.value)

        for name, value in self.__counters.items():
            rrdstats.counter(name, value)

    @adapter(ServiceCallReceived)
    def _updateWorkerItems(self, event):
        self.__counters["workerItems"] += 1

    @adapter(ServiceCallReceived)
    def _incrementWorkListCount(self, event):
        self.__counters[event.queue] += 1

    @adapter(ServiceCallCompleted)
    def _decrementWorkListCount(self, event):
        if event.retry is None:
            self.__counters[event.queue] -= 1
            if self.__counters[event.queue] < 0:
                log.warn(
                    "Worklist counter is negative count=%s worklist=%s",
                    self.__counters[event.queue],
                    event.queue,
                )

    @adapter(ServiceCallStarted)
    def _handleServiceCallStarted(self, event):
        """Update stats from the ServiceCallStarted event."""
        ws = self.__worker_stats[event.worker]
        ts = self.__task_stats[event.method]

        ws.status = "Busy"
        if ws.last_task:
            ws.idle += event.timestamp - ws.last_task.completed

        ws.current_task = _TaskInfo()
        ws.current_task.description = "%s.%s" % (event.service, event.method)
        ws.current_task.started = event.timestamp
        ts.count += 1

    @adapter(ServiceCallCompleted)
    def _handleServiceCallCompleted(self, event):
        """Update stats from the ServiceCallCompleted event."""
        ws = self.__worker_stats[event.worker]
        ts = self.__task_stats[event.method]

        ts.last_completed = event.timestamp
        ts.running_total += event.timestamp - ws.current_task.started

        ws.last_task = ws.current_task
        ws.last_task.completed = event.timestamp
        ws.current_task = None
        ws.status = "Idle"


class _TaskInfo(object):
    """Stats on a worker's current task."""

    __slots__ = ("description", "started", "completed")

    def __init__(self):
        self.description = ""
        self.started = None
        self.completed = None


class _WorkerStats(object):
    """Status of particular zenhubworker."""

    __slots__ = ("status", "current_task", "last_task", "idle")

    def __init__(self):
        self.status = ""
        self.current_task = None
        self.last_task = None
        self.idle = 0.0


class _TaskStats(object):
    """Status of a particular service call."""

    __slots__ = ("count", "running_total", "last_completed")

    def __init__(self):
        self.count = 0
        self.running_total = 0.0
        self.last_completed = 0.0
