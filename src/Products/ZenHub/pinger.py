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

from twisted.internet import defer, task

from .errors import HubDown


class PingZenHub(object):
    """Simple task to ping ZenHub."""

    def __init__(self, zenhub, interval=60):
        """
        Initialize a PingZenHub instance.

        @type zenhub: ZenHubClient
        @param interval: The number seconds between each ping.
        @type interval: float
        """
        self._zenhub = zenhub
        self._interval = interval
        self._loop = self._loopd = None
        self._log = logging.getLogger("zen.zenhub.ping")

    def start(self):
        self._loop = task.LoopingCall(self)
        self._loopd = self._loop.start(self._interval, now=False)

    def stop(self):
        if self._loop is None:
            return
        self._loop.stop()
        self._loop = self._loopd = None

    @defer.inlineCallbacks
    def __call__(self):
        # type: () -> defer.Deferred
        """Ping zenhub"""
        try:
            response = yield self._zenhub.ping()
            self._log.debug("pinged zenhub: %s", response)
        except HubDown:
            self._log.warning("no connection to zenhub")
        except Exception as ex:
            self._log.error("ping failed: %s", ex)
