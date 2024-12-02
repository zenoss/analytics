##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import math
import threading
import time

from itertools import chain

from Products.ZenUtils.controlplane import configuration as cc_config

from .logger import getLogger

# from itertools import izip_longest

# Metrics
# -------
# celery.<service>.pending.count - Count of queued tasks
# celery.<service>.running.count - Count of running tasks
# celery.<service>.cycletime.mean - Average runtime of tasks
# celery.<service>.leadtime.mean - Average lifetime of tasks
# celery.<service>.success.percent - Percentage of successful runs
# celery.<service>.failure.percent - Percentage of failed runs
# celery.<service>.retry.percent - Percentage of retried runs
#
# Where <service> is "zenjobs" or "builder" and <task-name> is the
# lower-cased name of the job.


class MetricsCollector(threading.Thread):
    def __init__(self, broker, inspector, reporter, metrics, interval=60):
        super(MetricsCollector, self).__init__()
        self._broker = broker
        self._inspector = inspector
        self._metrics = metrics
        self._reporter = reporter
        self._interval = interval
        self._stopEvent = threading.Event()
        self._log = getLogger(self)

    def stop(self):
        self._stopEvent.set()

    def run(self):
        while not self._stopEvent.is_set():
            self._stopEvent.wait(self._interval)
            if not self._stopEvent.is_set():
                try:
                    self.task()
                except Exception:
                    self._log.exception("error while collecting metrics")

    def task(self):
        self._log.debug("begin metric collection")
        try:
            running_counts = self._inspector.running_counts()
            if not running_counts:
                self._log.warning("count of running tasks not collected")
            services = self._inspector.workers()
            if not services:
                self._log.warning("no information about workers")
            queues = {
                str(queue["name"]): queue["messages"]
                for queue in self._broker.queues(
                    [info["queue"] for info in services.values()]
                )
            }
            if not queues:
                self._log.warning("no information about queues")
            report = self._metrics.report()

            mgen = _MetricGenerator(services, running_counts, queues, report)

            common_tags = {
                "serviceId": cc_config.service_id,
                "tenantId": cc_config.tenant_id,
            }
            with self._reporter.session(tags=common_tags) as session:
                for metric in mgen():
                    session.add(**metric)

                if self._log.getEffectiveLevel() == logging.DEBUG:
                    for metric in session.metrics:
                        self._log.debug(metric)
        finally:
            self._log.debug("finished metric collection")


class _MetricGenerator(object):
    def __init__(self, services, running_counts, queues, report):
        self._now = time.time()
        self._running_counts = running_counts
        self._services = services
        self._serviceids = {
            str(name): str(info["serviceid"])
            for name, info in services.iteritems()
        }
        self._queues = queues
        self._report = report

    def __call__(self):
        return chain(self._counts(), self._percents(), self._timings())

    def _counts(self):
        for service, info in self._services.iteritems():
            pending_count = self._queues.get(info["queue"])
            if pending_count is not None:
                yield (
                    {
                        "metric": "celery.{}.pending.count".format(service),
                        "value": pending_count,
                        "timestamp": self._now,
                    }
                )
            running_count = self._running_counts.get(service)
            if running_count is not None:
                yield (
                    {
                        "metric": "celery.{}.running.count".format(service),
                        "value": running_count,
                        "timestamp": self._now,
                    }
                )

    def _percents(self):
        results = self._report.get("results")
        for service, result in results.iteritems():
            success = result["success_percent"]
            failure = result["failure_percent"]
            retry = result["retry_percent"]
            if not math.isnan(success):
                yield (
                    {
                        "metric": "celery.{}.success.percent".format(service),
                        "value": success,
                        "timestamp": self._now,
                    }
                )
            if not math.isnan(failure):
                yield (
                    {
                        "metric": "celery.{}.failure.percent".format(service),
                        "value": failure,
                        "timestamp": self._now,
                    }
                )
            if not math.isnan(retry):
                yield (
                    {
                        "metric": "celery.{}.retry.percent".format(service),
                        "value": retry,
                        "timestamp": self._now,
                    }
                )

    def _timings(self):
        cycletime_services = self._report["cycletime"]["services"]
        leadtime_services = self._report["leadtime"]["services"]
        for service, cycletimes in cycletime_services.iteritems():
            yield (
                {
                    "metric": "celery.{}.cycletime.mean".format(service),
                    "value": cycletimes["mean"],
                    "timestamp": self._now,
                }
            )
            leadtimes = leadtime_services.get(service)
            yield (
                {
                    "metric": "celery.{}.leadtime.mean".format(service),
                    "value": leadtimes["mean"],
                    "timestamp": self._now,
                }
            )
