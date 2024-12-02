##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from collections import defaultdict

from .logger import getLogger


class Inspector(object):
    """Just enough API to satisfy collecting metrics from Celery."""

    def __init__(self, app, timeout=10):
        self._app = app
        self._timeout = timeout
        self._workers = defaultdict(dict)
        self._log = getLogger(self)

    def running_counts(self):
        inspect = self._app.control.inspect(timeout=self._timeout)
        result = inspect.active()
        if result is None or "error" in result:
            self._log.warning("inspect method 'active' failed: %s", result)
            return {}
        running = {}
        for node, tasks in result.items():
            service = _get_service_from_node(node)
            count = running.get(service, 0)
            running[service] = count + len(tasks)
        return running

    def workers(self):
        inspect = self._app.control.inspect(timeout=self._timeout)
        result = inspect.active_queues()
        if result is None or "error" in result:
            self._log.warning(
                "inspect method 'active_queues' failed: %s", result
            )
            return {}
        return {
            _get_service_from_node(node): {
                "serviceid": _get_serviceid_from_node(node),
                "queue": data[0]["name"],
            }
            for node, data in result.items()
        }


def _get_serviceid_from_node(node):
    return node.split("@")[1]


def _get_service_from_node(node):
    return node.split("@")[0].split("-")[0]
