##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.spread import pb
from zenoss.protocols.services import ServiceConnectionError

from Products.ZenEvents.Event import Event
from Products.ZenHub.errors import translateError
from Products.ZenHub.HubService import HubService
from Products.Zuul import getFacade

from .ThresholdMixin import ThresholdMixin

pb.setUnjellyableForClass(Event, Event)
log = logging.getLogger("zen.EventService")


class EventService(HubService, ThresholdMixin):
    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.conf = self.dmd.Monitors.Performance._getOb(self.instance)

    @translateError
    def remote_sendEvent(self, evt):
        try:
            val = self.zem.sendEvent(evt)
            return val
        except Exception as ex:
            log.exception(ex)

    @translateError
    def remote_sendEvents(self, evts):
        return self.zem.sendEvents(evts)

    @translateError
    def remote_getDevicePingIssues(self, *args, **kwargs):
        zep = getFacade("zep")
        try:
            return zep.getDevicePingIssues()
        except ServiceConnectionError:
            # ZEN-503: Don't print a traceback in this case
            log.warn("Unable to contact ZEP.")
            return None

    @translateError
    def remote_getDeviceIssues(self, *args, **kwargs):
        zep = getFacade("zep")
        try:
            return zep.getDeviceIssues()
        except ServiceConnectionError:
            # ZEN-503: Don't print a traceback in this case
            log.warn("Unable to contact ZEP.")
            return None

    @translateError
    def remote_getDefaultPriority(self):
        return self.zem.defaultPriority
