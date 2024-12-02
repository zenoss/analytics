##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections
import json
import logging
import os
import re
import subprocess
import sys
import time

import ZPublisher.interfaces

from Products.Five.browser import BrowserView
from zope import component, interface
from ZServer.PubCore.ZRendezvous import ZRendevous

from Products.Zuul import interfaces
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenUtils.cstat import CStat
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.requestlogging.ZopeRequestLogger import (
    ZopeRequestLogger,
)

_LOG = logging.getLogger("zen.stats")

_request_logger = ZopeRequestLogger()

_request_threshold = float(
    getGlobalConfiguration().get("zope-request-threshold", 5.0)
)


# hook in to Web Server's Request Events so that
# fine grained monitoring can be done
@component.adapter(ZPublisher.interfaces.IPubStart)
def logRequestStart(event):
    event.request._start = time.time()


@component.adapter(ZPublisher.interfaces.IPubAfterTraversal)
def logRequestStartAfterTraversal(event):
    # When IPubAfterTraversal is triggered the request body is available
    # in event.request
    try:
        _request_logger.log_request(event.request)
    except Exception:
        pass


@component.adapter(ZPublisher.interfaces.IPubEnd)
def logRequestEnd(event):
    global _REQUEST_TOTAL, _REQUEST_COUNT, _REQUEST_TIME
    global _SLOW_REQUEST_COUNT, _SLOW_REQUEST_TIME, _SLOW_REQUEST_TOTAL
    ts = time.time()
    elapsed = ts - event.request._start
    _REQUEST_TOTAL += 1
    _REQUEST_COUNT.save(1, ts)
    _REQUEST_TIME.save(elapsed, ts)

    if elapsed >= _request_threshold:
        _SLOW_REQUEST_TOTAL += 1
        _SLOW_REQUEST_COUNT.save(1, ts)
        _SLOW_REQUEST_TIME.save(elapsed, ts)

    try:
        _request_logger.log_request(event.request, finished=True)
    except Exception:
        pass


_STATS_PERIOD = 60 * 15  # keep in-memory stats for 15 minutes
_REQUEST_TOTAL = 0  # running total of http requests
_REQUEST_COUNT = CStat(_STATS_PERIOD)  # CStat of request count
_REQUEST_TIME = CStat(_STATS_PERIOD)  # Cstat of request service times
_SLOW_REQUEST_TOTAL = 0
_SLOW_REQUEST_COUNT = CStat(_STATS_PERIOD)
_SLOW_REQUEST_TIME = CStat(_STATS_PERIOD)

_BYTES_MAP = {
    "b": 1,
    "k": 1024,
    "kb": 1024,
    "m": 1024 * 1024,
    "mb": 1024 * 1024,
    "g": 1024 * 1024 * 1024,
    "gb": 1024 * 1024 * 1024,
}


@interface.implementer(interfaces.ISystemMetric)
class _ZodbMetrics(object):
    """
    Base class for reporting ZODB metrics.
    """

    component.adapts(DataRoot)

    db = None

    def __init__(self, context):
        self.context = context
        self._db = None

    def metrics(self):
        metrics = {}
        end = time.time()
        start = end - 60
        db = self.context.unrestrictedTraverse(
            "/Control_Panel/Database/%s" % self.db
        )
        args = {
            "chart_start": start,
            "chart_end": end,
        }
        activityChart = db.getActivityChartData(200, args)
        metrics["totalLoadCount"] = activityChart["total_load_count"]
        metrics["totalStoreCount"] = activityChart["total_store_count"]
        metrics["totalConnections"] = activityChart["total_connections"]
        metrics["cacheLength"] = db.cache_length()
        metrics["cacheSize"] = db.cache_size()

        # convert dbsize from string to bytes
        dbSize = db.db_size()
        match = re.search(
            r"(?P<value>[0-9]*\.?[0-9]*)(?P<unit>[^0-9]+)", dbSize
        )
        metrics["databaseSize"] = int(
            float(match.group(1)) * _BYTES_MAP[match.group(2).lower()]
        )

        return metrics


class MainZodbMetrics(_ZodbMetrics):
    db = "main"
    category = "ZODB_main"


class TempZodbMetrics(_ZodbMetrics):
    db = "temporary"
    category = "ZODB_temp"


@interface.implementer(interfaces.ISystemMetric)
class ZopeMetrics(object):
    """
    ZopeMetrics reports metric related to the Zope server.
    """

    component.adapts(DataRoot)

    def __init__(self, context):
        self.context = context

    category = "Zope"

    def metrics(self):
        metrics = {}

        # get total threads
        metrics["totalThreads"] = len(sys._current_frames().keys())

        # get free threads
        freeThreads = 0
        for frame in sys._current_frames().values():
            _self = frame.f_locals.get("self")
            if getattr(_self, "__module__", None) == ZRendevous.__module__:
                freeThreads += 1
        metrics["freeThreads"] = freeThreads

        try:
            metrics["activeSessions"] = len(
                self.context.unrestrictedTraverse("/temp_folder/session_data")
            )
        except Exception:
            metrics["activeSessions"] = -1

        global _REQUEST_TOTAL, _REQUEST_COUNT, _REQUEST_TIME
        metrics["requestTotal"] = _REQUEST_TOTAL
        metrics["request1m"] = max(_REQUEST_COUNT.query(60), 1)
        metrics["requestTimeAvg1m"] = _REQUEST_TIME.query(60) / float(
            metrics["request1m"]
        )

        # Number of requests exceeding zope-request-threshold
        global _SLOW_REQUEST_COUNT, _SLOW_REQUEST_TIME, _SLOW_REQUEST_TOTAL
        metrics["slowRequestTotal"] = _SLOW_REQUEST_TOTAL
        metrics["slowRequest1m"] = _SLOW_REQUEST_COUNT.query(60)

        try:
            metrics["slowRequestTimeAvg1m"] = _SLOW_REQUEST_TIME.query(
                60
            ) / float(metrics["slowRequest1m"])
        except ZeroDivisionError:
            # No slow requests
            metrics["slowRequestTimeAvg1m"] = 0.0

        # request1m is always 1 or greater
        metrics["slowRequestPercent"] = (
            float(metrics["slowRequest1m"]) / metrics["request1m"]
        ) * 100

        for key, value in self._getVmStats():
            metrics[key] = value

        return metrics

    def _getVmStats(self):
        """
        _getVmStats() retrives memory usage for the current process
        """
        try:
            vmLines = subprocess.check_output(
                "cat /proc/%d/status | egrep ^Vm" % os.getpid(), shell=True
            )
            for line in vmLines.splitlines():
                rawStat, rawValue, unit = (line.split() + ["B"])[0:3]
                stat = rawStat.split(":")[0]
                value = int(float(rawValue) * _BYTES_MAP[unit.lower()])
                yield stat, value
        except subprocess.CalledProcessError as ex:
            _LOG.warn("Could not get memory info for current process: %s" % ex)


class StatsView(BrowserView):
    """
    Provide a window in to this Zenoss Instance's performance stats.
    """

    def __call__(self):
        metrics = collections.defaultdict(lambda: {})
        for subscriber in component.subscribers(
            (self.context.dmd,), interfaces.ISystemMetric
        ):
            try:
                metrics[subscriber.category].update(subscriber.metrics())
            except Exception as ex:
                _LOG.warn(
                    "An error occurred gathering performance stats: %s" % ex
                )

        self.request.response.write(json.dumps(metrics))
