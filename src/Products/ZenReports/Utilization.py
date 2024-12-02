##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.AdvancedQuery import MatchGlob, And

from Products.ZenUtils import Time
from Products.Zuul.catalog.interfaces import IModelCatalogTool

log = logging.getLogger("zen.Utilization")


def getSummaryArgs(dmd, args):
    zem = dmd.ZenEventManager
    startDate = args.get("startDate", zem.defaultAvailabilityStart())
    endDate = args.get("endDate", zem.defaultAvailabilityEnd())
    startDate, endDate = map(Time.ParseUSDate, (startDate, endDate))
    endDate = Time.getEndOfDay(endDate)
    startDate = min(
        startDate, endDate - 24 * 60 * 60 + 1
    )  # endDate - 23:59:59
    how = args.get("how", "AVERAGE")
    cfhow = args.get("cfhow", "AVERAGE")
    return dict(start=startDate, end=endDate, function=how, cf=cfhow)


def reversedSummary(summary):
    swapper = {"MAXIMUM": "MINIMUM", "MINIMUM": "MAXIMUM"}
    summary = summary.copy()
    current = summary["function"]
    summary["function"] = swapper.get(current, current)
    return summary


def filteredDevices(context, args, *types):
    path = "/zport/dmd"

    deviceFilter = args.get("deviceFilter", "") or ""
    deviceClass = args.get("deviceClass", "") or ""
    extraquery = args.get("extraquery", "")
    filter = []
    if deviceFilter:
        filter.append(
            MatchGlob("name", "*%s*" % deviceFilter)
            | MatchGlob("id", "*%s*" % deviceFilter)
        )
    if deviceClass:
        organizer = ("".join([path, deviceClass]),)
    else:
        organizer = (
            "".join([path, args.get("organizer", "/Devices") or "/Devices"]),
        )

    if not types:
        types = "Products.ZenModel.Device.Device"

    if extraquery:
        filter.extend(extraquery)

    query = And(*filter) if filter else None

    results = IModelCatalogTool(context).search(
        types, paths=organizer, query=query
    )

    for brain in results:
        try:
            yield brain.getObject()
        except Exception:
            log.warn("Unable to unbrain at path %s", brain.getPath())
