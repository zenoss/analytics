##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from HubService import HubService
from twisted.internet import reactor
import time


class Beat(HubService):
    """Example service which sends a simple heartbeat to keep a client
    connection alive."""

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.beat()

    def beat(self):
        secs = time.time()
        for listener in self.listeners:
            d = listener.callRemote("beat", secs)
            d.addErrback(self.error)
        reactor.callLater(1, self.beat)

    def error(self, reason, unused):
        reason.printTraceback()
