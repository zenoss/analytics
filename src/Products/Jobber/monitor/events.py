##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import threading
import time

from celery.events import EventReceiver

from .logger import getLogger


class EventsMonitor(threading.Thread):

    daemon = True  # doesn't block shutdown

    def __init__(self, sink, app):
        """Initialize an EventsMonitor instance.

        @param sink: Events are written to this object.
        @type sink: Queue.Queue
        @param app: The Celery application
        @type app: celery.Celery
        """
        super(EventsMonitor, self).__init__()
        self._sink = sink
        self._app = app
        self._log = getLogger(self)

    def run(self):
        try_interval = 1
        while True:
            try:
                try_interval *= 2
                with self._app.connection() as conn:
                    recv = EventReceiver(
                        conn, handlers={"*": self._put}, app=self._app
                    )
                    try_interval = 1
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except Exception:
                self._log.exception("unexpected error")
                time.sleep(try_interval)

    def _put(self, event):
        self._sink.put(event)
