##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_ACKNOWLEDGED,
    STATUS_NEW,
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
)
from Products.ZenReports.AliasPlugin import AliasPlugin
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.Zuul import getFacade

log = logging.getLogger("zen.reports")


class snmpstatusreport(AliasPlugin):
    """
    Gets a list of devices based on if they have snmp status issues
    """

    def _getEvents(self, dmd, eventClass):
        """
        Returns all the open critical, warning or error events for
        the event class.
        """
        zep = getFacade("zep", dmd)
        event_filter = zep.createEventFilter(
            severity=[SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL],
            status=[STATUS_NEW, STATUS_ACKNOWLEDGED],
            event_class=filter(None, [eventClass]),
        )

        return zep.getEventSummaries(0, filter=event_filter)

    def _getDevices(self, dmd, results):
        """
        Look up the devices from the events.
        """
        manager = IGUIDManager(dmd)
        events = results["events"]
        for event in events:
            occurrence = event["occurrence"][0]
            actor_uuid = occurrence["actor"].get("element_uuid")
            if not actor_uuid:
                continue
            dev = manager.getObject(actor_uuid)
            if dev:
                yield dev

    def run(self, dmd, args):
        # ZEN-30539
        if args.get("adapt", ""):
            return []
        eventClass = "/Status/Snmp"
        results = self._getEvents(dmd, eventClass)
        return self._getDevices(dmd, results)
