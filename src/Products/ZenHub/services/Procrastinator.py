##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from twisted.internet import reactor, defer

log = logging.getLogger("zen.Procrastinator")


class Procrastinate(object):
    "A class to delay executing a change to a device"

    _DO_LATER_DELAY = 5
    _DO_NOW_DELAY = 0.05

    def __init__(self, cback):
        self.cback = cback
        self.devices = set()
        self.timer = None
        self._stopping = False
        self._stopping_deferred = defer.Deferred()

    def clear(self):
        self.devices = set()

    def stop(self):
        self._stopping = True
        if not self.devices:
            return defer.succeed(True)
        log.debug("Returning stopping deferred")
        d, self._stopping_deferred = self._stopping_deferred, None
        return d

    def doLater(self, device=None):
        if not self._stopping:
            if self.timer and not self.timer.called:
                self.timer.cancel()
            self.devices.add(device)
            self.timer = reactor.callLater(
                Procrastinate._DO_LATER_DELAY, self._doNow
            )

    def _doNow(self, *unused):
        if self.devices:
            device = self.devices.pop()
            self.cback(device)
            if self.devices:
                reactor.callLater(Procrastinate._DO_NOW_DELAY, self._doNow)
            elif self._stopping:
                log.debug("Callback to _stopping_deferred")
                self._stopping_deferred.callback(None)
