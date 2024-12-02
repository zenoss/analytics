##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import Queue
import threading

from collections import defaultdict

from celery.events.state import State

from .logger import getLogger


class EventsHandler(threading.Thread):
    def __init__(self, source, metrics, app):
        """Initialize an EventsHandler instance.

        @param source: Events are read from this object.
        @type source: Queue.Queue
        @param metrics:
        @type metrics: ZenJobsMetrics
        @param app: The Celery application
        @type app: celery.Celery
        """
        super(EventsHandler, self).__init__()
        self._source = source
        self._metrics = metrics
        self._app = app
        self._stopEvent = threading.Event()
        self._queue_svc_map = {}
        self._handlers = {
            "worker-online": self._online,
            "worker-offline": self._offline,
            "task-sent": self._sent,
            "task-succeeded": self._succeeded,
            "task-retried": self._retried,
            "task-failed": self._failed,
        }
        self._heartbeats = defaultdict(int)
        self._log = getLogger(self)

    def run(self):
        self._log.info("started handling celery events")
        state = State()
        while not self._stopEvent.is_set():
            try:
                event = self._source.get(True, 0.5)
                state.event(event)

                event_type = event["type"]

                handler = self._handlers.get(event_type)
                if not handler:
                    continue

                if event_type.startswith("task-"):
                    task_id = event["uuid"]
                    arg = state.tasks.get(task_id)
                else:
                    arg = state.workers.get(event["hostname"])

                try:
                    handler(arg)
                except Exception:
                    self._log.exception("event handler failed: %r", handler)
            except Queue.Empty:
                pass
            except Exception:
                self._log.exception("unexpected error")
        self._log.info("stopped handling celery events")

    def stop(self):
        self._stopEvent.set()

    def _get_svc_from_node(self, node):
        return node.split("@")[0].split("-")[0]

    def _online(self, worker):
        self._log.info("worker online  worker=%s", worker.hostname)

    def _offline(self, worker):
        self._log.warning("worker offline  worker=%s", worker.hostname)

    def _build_queue_svc_mapping(self):
        inspect = self._app.control.inspect()
        active_queues = inspect.active_queues()
        for node, queues in active_queues.items():
            svcname = self._get_svc_from_node(node)
            qname = queues[0]["name"]
            if qname not in self._queue_svc_map:
                self._queue_svc_map[qname] = svcname

    def _get_svc_from_queue(self, qname):
        if qname not in self._queue_svc_map:
            self._build_queue_svc_mapping()
        return self._queue_svc_map.get(qname)

    def _sent(self, task):
        if not task.sent:
            return
        svcid = self._get_svc_from_queue(task.queue)
        if svcid is None:
            self._log.warning(
                "no service for tasks on queue '%s' found", task.queue
            )
        else:
            with self._metrics as updater:
                updater.count_sent(svcid)

    def _succeeded(self, task):
        if not task.received or not task.started:
            return
        svcid = self._get_svc_from_node(task.hostname)
        with self._metrics as updater:
            updater.mark_success(svcid)
            updater.add_task_runtime(svcid, task.name, task.runtime)
            _completed(task, svcid, updater)

    def _failed(self, task):
        svcid = self._get_svc_from_node(task.hostname)
        with self._metrics as updater:
            updater.mark_failure(svcid)
            _completed(task, svcid, updater)

    def _retried(self, task):
        svcid = self._get_svc_from_node(task.hostname)
        with self._metrics as updater:
            updater.mark_retry(svcid)
            _completed(task, svcid, updater)


def _completed(task, svcid, metrics):
    if not task.sent:
        return
    leadtime = task.timestamp - task.sent
    metrics.count_completed(svcid)
    metrics.add_task_leadtime(svcid, task.name, leadtime)
