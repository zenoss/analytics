##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""The threshold report."""

import time

from collections import defaultdict
from itertools import chain

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_WARNING

from Products.ZenEvents.Availability import (
    Availability,
    CLOSED_EVENT_STATUSES,
    _severityGreaterThanOrEqual,
)
from Products.ZenReports import Utils
from Products.ZenUtils.Time import Duration, getBeginningOfDay, getEndOfDay
from Products.Zuul import getFacade


def dateAsFloat(args, key, default):
    from Products.ZenUtils.Time import ParseUSDate

    if key in args:
        args[key] = ParseUSDate(args[key])
    else:
        args[key] = default


class threshold(object):
    def run(self, dmd, args):
        # ZEN-30539
        if args.get("adapt", ""):
            return []
        now = time.time()
        zep = getFacade("zep", dmd)

        # read in args
        dateAsFloat(
            args, "startDate", Availability.getDefaultAvailabilityStart(dmd)
        )
        dateAsFloat(args, "endDate", Availability.getDefaultAvailabilityEnd())
        args["eventClass"] = args.get("eventClass", "") or "/Perf"

        startDate = min(args["startDate"], now)
        endDate = min(args["endDate"], now)
        startDate = getBeginningOfDay(startDate)
        endDate = getEndOfDay(endDate)
        if endDate <= startDate:
            return []

        # Convert start and end date to integer milliseconds for
        # defining filters.
        startDate = int(startDate * 1000)
        endDate = int(endDate * 1000)

        # Compose filter for retrieval from ZEP
        create_filter_args = {
            "severity": _severityGreaterThanOrEqual(SEVERITY_WARNING),
            "event_class": args["eventClass"]
            + ("/" if not args["eventClass"].endswith("/") else ""),
            "first_seen": (0, endDate),
            "last_seen": (startDate,),
        }
        event_filter = zep.createEventFilter(**create_filter_args)
        events = zep.getEventSummariesGenerator(event_filter)
        events_from_archive = zep.getEventSummariesGenerator(
            event_filter, archive=True
        )

        sum = defaultdict(int)
        counts = defaultdict(int)
        for evtsumm in chain(events, events_from_archive):

            first = evtsumm["first_seen_time"]
            # If event is still open, downtime persists til end of
            # report window.
            if evtsumm["status"] not in CLOSED_EVENT_STATUSES:
                last = endDate
            else:
                last = evtsumm["status_change_time"]

            # clip first and last within report time window
            first = max(first, startDate)
            last = min(last, endDate)

            # discard any events that have no elapsed time
            if first == last:
                continue

            # extract key fields, and update time/count tallies
            evt = evtsumm["occurrence"][0]
            evt_actor = evt["actor"]
            device = evt_actor.get("element_identifier")
            component = evt_actor.get("element_sub_identifier")
            eventClass = evt["event_class"]

            diff = last - first
            sum[(device, component, eventClass)] += diff
            counts[(device, component, eventClass)] += 1

        # Look up objects that correspond to the names
        report = []
        find = dmd.Devices.findDevice
        totalTime = endDate - startDate
        for k, seconds in sum.items():
            deviceName, componentName, eventClassName = k
            deviceLink = deviceName
            component = None
            componentLink = componentName
            eventClass = None
            eventClassLink = eventClassName
            device = find(deviceName)
            if not device or not dmd.checkRemotePerm("View", device):
                continue
            deviceLink = device.urlLink()
            if componentName:
                for c in device.getMonitoredComponents():
                    if c.name().find(componentName) >= 0:
                        component = c
                        componentLink = c.urlLink()
                        break
            # get some values useful for the report
            duration = Duration(seconds / 1000)
            percent = seconds * 100.0 / totalTime
            try:
                eventClass = dmd.Events.getOrganizer(eventClassName)
                eventClassLink = eventClass.urlLink()
            except KeyError:
                pass
            report.append(
                Utils.Record(
                    deviceName=deviceName,
                    deviceLink=deviceLink,
                    componentName=componentName,
                    componentLink=componentLink,
                    eventClassName=eventClassName,
                    eventClassLink=eventClassLink,
                    count=counts.get(k, 1),
                    seconds=seconds,
                    percentTime=percent,
                    duration=duration,
                )
            )

        return report
