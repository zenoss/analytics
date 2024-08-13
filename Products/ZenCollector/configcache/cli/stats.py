##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import, division

import argparse
import sys
import time

import attr

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app import initialize_environment
from ..app.args import get_subparser
from ..cache import DeviceQuery

from .args import get_common_parser, MultiChoice
from ._tables import TablesOutput, _xform
from ._json import JSONOutput
from ._stats import (
    AverageAgeStat,
    CountStat,
    MaxAgeStat,
    MedianAgeStat,
    MinAgeStat,
    UniqueCountStat,
)
from ._groups import DeviceGroup, ServiceGroup, MonitorGroup, StatusGroup


class Stats(object):
    description = "Show statistics about the configurations"

    @staticmethod
    def add_arguments(parser, subparsers):
        statsp = get_subparser(
            subparsers,
            "stats",
            description=Stats.description,
        )
        show_subparsers = statsp.add_subparsers(title="Stats Subcommands")
        StatsDevices.add_arguments(statsp, show_subparsers)
        StatsOidMap.add_arguments(statsp, show_subparsers)


class StatsOidMap(object):
    description = "Show the statistics of the oidmap configuration"
    configs = (("stats.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "oidmap",
            description=StatsOidMap.description,
        )
        subp.set_defaults(factory=StatsOidMap)

    def __init__(self, args):
        pass

    def run(self):
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("oidmapcache-store", client)
        record = store.get()
        status = store.get_status()
        if record is None and status is None:
            print("No oidmap found in the cache.")
        else:
            now = time.time()
            if record is not None:
                age = now - record.created
                print("Oidmap Age: {}".format(_xform(age, "timedelta")))
            else:
                print("no oidmap")
            if status is not None:
                status_text = type(status).__name__
                print("Status: {}".format(status_text))
                ts = attr.astuple(status)[-1]
                age = now - ts
                print("Status Age: {}".format(_xform(age, "timedelta")))


class StatsDevices(object):
    description = "Show statistics about the device configurations"
    configs = (("stats.zcml", __name__),)

    _groups = ("collector", "device", "service", "status")
    _statistics = ("count", "avg_age", "median_age", "min_age", "max_age")

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "device",
            StatsDevices.description,
            parent=get_common_parser(),
        )
        subp.add_argument(
            "-S",
            dest="statistic",
            action=MultiChoice,
            choices=StatsDevices._statistics,
            default=argparse.SUPPRESS,
            help="Specify the statistics to return.  One or more statistics "
            "may be specified (comma separated). By default, all "
            "statistics are returned.",
        )
        subp.add_argument(
            "-G",
            dest="group",
            action=MultiChoice,
            choices=StatsDevices._groups,
            default=argparse.SUPPRESS,
            help="Specify the statistics groupings to return.  One or more "
            "groupings may be specified (comma separated). By default, all "
            "groupings are returned.",
        )
        subp.add_argument(
            "-f",
            dest="format",
            choices=("tables", "json"),
            default="tables",
            help="Output statistics in the specified format",
        )
        subp.set_defaults(factory=StatsDevices)

    def __init__(self, args):
        stats = []
        for statId in getattr(args, "statistic", StatsDevices._statistics):
            if statId == "count":
                stats.append(CountStat)
            elif statId == "avg_age":
                stats.append(AverageAgeStat)
            elif statId == "median_age":
                stats.append(MedianAgeStat)
            elif statId == "min_age":
                stats.append(MinAgeStat)
            elif statId == "max_age":
                stats.append(MaxAgeStat)
        self._groups = []
        for groupId in getattr(args, "group", StatsDevices._groups):
            if groupId == "collector":
                self._groups.append(MonitorGroup(stats))
            elif groupId == "device":
                try:
                    # DeviceGroup doesn't want CountStat
                    posn = stats.index(CountStat)
                except ValueError:
                    # Not found, so don't worry about it
                    dg_stats = stats
                    pass
                else:
                    # Found, replace it with UniqueCountStat
                    dg_stats = list(stats)
                    dg_stats[posn] = UniqueCountStat
                self._groups.append(DeviceGroup(dg_stats))
            if groupId == "service":
                self._groups.append(ServiceGroup(stats))
            elif groupId == "status":
                self._groups.append(StatusGroup(stats))
        if args.format == "tables":
            self._format = TablesOutput()
        elif args.format == "json":
            self._format = JSONOutput()
        self._monitor = "*{}*".format(args.collector).replace("***", "*")
        self._service = "*{}*".format(args.service).replace("***", "*")
        self._devices = getattr(args, "device", [])

    def run(self):
        haswildcard = any("*" in d for d in self._devices)
        if haswildcard and len(self._devices) > 1:
            print(
                "Only one DEVICE argument supported when a wildcard is used.",
                file=sys.stderr,
            )
            return
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("deviceconfigcache-store", client)

        if len(self._devices) == 1:
            query = DeviceQuery(self._service, self._monitor, self._devices[0])
        else:
            query = DeviceQuery(self._service, self._monitor)
        include = _get_device_predicate(self._devices)
        for key, ts in store.query_updated(query):
            if not include(key.device):
                continue
            for group in self._groups:
                group.handle_key(key)
                group.handle_timestamp(key, ts)
        for status in store.query_statuses(query):
            if not include(status.key.device):
                continue
            for group in self._groups:
                group.handle_status(status)

        self._format.write(
            *(group for group in sorted(self._groups, key=lambda x: x.order))
        )


def _get_device_predicate(devices):
    if len(devices) < 2:
        return lambda _: True
    return lambda x: next((True for d in devices if x == d), False)
