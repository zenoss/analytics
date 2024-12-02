##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from collections import defaultdict
from threading import RLock

from metrology.instruments import HistogramUniform, Meter
from metrology.instruments.gauge import PercentGauge


class ZenJobsMetrics(object):
    def __init__(self):
        self._lock = RLock()  # synchronize thread access
        self._metrics = _BagOfMetrics()

    def __enter__(self):
        self._lock.acquire()
        return self._metrics

    def __exit__(self, *exc_info):
        self._lock.release()

    def report(self):
        with self._lock:
            cycletime = _get_timings(
                self._metrics.cycletime,
                self._metrics.cycletime_task,
                self._metrics.cycletime_service,
                self._metrics.cycletime_service_task,
            )
            leadtime = _get_timings(
                self._metrics.leadtime,
                self._metrics.leadtime_task,
                self._metrics.leadtime_service,
                self._metrics.leadtime_service_task,
            )

            results = {
                service: {
                    "success_rate": self._metrics.successes[service].mean_rate,
                    "success_percent": self._metrics.success_pct[
                        service
                    ].value,
                    "retry_rate": self._metrics.retries[service].mean_rate,
                    "retry_percent": self._metrics.retry_pct[service].value,
                    "failure_rate": self._metrics.failures[service].mean_rate,
                    "failure_percent": self._metrics.failure_pct[
                        service
                    ].value,
                }
                for service in self._metrics.services
            }

            return {
                "cycletime": cycletime,
                "leadtime": leadtime,
                "results": results,
            }


class _BagOfMetrics(object):
    def __init__(self):
        # cache of service IDs
        self.services = set()

        # Task runtimes;
        # {service-id: {task-name: histogram}}
        self.cycletime_service_task = {}
        # {task-name: histogram}
        self.cycletime_task = {}
        # {service-id: histogram}
        self.cycletime_service = {}
        # All tasks on all services
        self.cycletime = HistogramUniform()

        # Total lifetime of tasks;
        # {service-id: {task-name: histogram}}
        self.leadtime_service_task = {}
        # {task-name: histogram}
        self.leadtime_task = {}
        # {service-id: histogram}
        self.leadtime_service = {}
        # All tasks on all services
        self.leadtime = HistogramUniform()

        # Task run rates
        # {service-id: meter}
        self.failures = defaultdict(Meter)
        self.retries = defaultdict(Meter)
        self.successes = defaultdict(Meter)
        self.completed = defaultdict(Meter)

        # Percentages by service
        # {service-id: PercentGauge}
        self.success_pct = PercentMetricsGroup(self.successes, self.completed)
        self.failure_pct = PercentMetricsGroup(self.failures, self.completed)
        self.retry_pct = PercentMetricsGroup(self.retries, self.completed)

    def add_task_runtime(self, service, task, runtime):
        millisecs = int(runtime * 1000)

        if service not in self.cycletime_service_task:
            self.cycletime_service_task[service] = {}
        if task not in self.cycletime_service_task[service]:
            self.cycletime_service_task[service][task] = HistogramUniform()
        self.cycletime_service_task[service][task].update(millisecs)

        if task not in self.cycletime_task:
            self.cycletime_task[task] = HistogramUniform()
        self.cycletime_task[task].update(millisecs)

        if service not in self.cycletime_service:
            self.cycletime_service[service] = HistogramUniform()
        self.cycletime_service[service].update(millisecs)

        self.cycletime.update(millisecs)
        self.services.add(service)

    def add_task_leadtime(self, service, task, leadtime):
        millisecs = int(leadtime * 1000)

        if service not in self.leadtime_service_task:
            self.leadtime_service_task[service] = {}
        if task not in self.leadtime_service_task[service]:
            self.leadtime_service_task[service][task] = HistogramUniform()
        self.leadtime_service_task[service][task].update(millisecs)

        if task not in self.leadtime_task:
            self.leadtime_task[task] = HistogramUniform()
        self.leadtime_task[task].update(millisecs)

        if service not in self.leadtime_service:
            self.leadtime_service[service] = HistogramUniform()
        self.leadtime_service[service].update(millisecs)

        self.leadtime.update(millisecs)
        self.services.add(service)

    def count_sent(self, service):
        self.services.add(service)

    def count_completed(self, service):
        self.completed[service].mark()
        self.services.add(service)

    def mark_success(self, service):
        self.successes[service].mark()
        self.services.add(service)

    def mark_retry(self, service):
        self.retries[service].mark()
        self.services.add(service)

    def mark_failure(self, service):
        self.failures[service].mark()
        self.services.add(service)


def _get_timings(total, bytask, byservice, byservicetask):
    return {
        "min": total.min,
        "mean": total.mean,
        "max": total.max,
        "tasks": {
            task: {"min": metric.min, "mean": metric.mean, "max": metric.max}
            for task, metric in bytask.iteritems()
        },
        "services": {
            service: {
                "min": metric.min,
                "mean": metric.mean,
                "max": metric.max,
                "tasks": {
                    task: {
                        "min": metric.min,
                        "mean": metric.mean,
                        "max": metric.max,
                    }
                    for task, metric in byservicetask.get(
                        service, {}
                    ).iteritems()
                },
            }
            for service, metric in byservice.iteritems()
        },
    }


class PercentMetricsGroup(object):
    def __init__(self, numerators, denominators):
        self._nums = numerators
        self._dens = denominators
        self._metrics = {}

    def get(self, name, default=None):
        metric = self._metrics.get(name)
        if metric is None:
            metric = _TwoCountersGauge(self._nums[name], self._dens[name])
            self._metrics[name] = metric
        return metric

    def __getitem__(self, key):
        return self.get(key)


class _TwoCountersGauge(PercentGauge):
    def __init__(self, numerator, denominator):
        self._num = numerator
        self._den = denominator

    # @override
    def numerator(self):
        return self._num.count

    # @override
    def denominator(self):
        return self._den.count
