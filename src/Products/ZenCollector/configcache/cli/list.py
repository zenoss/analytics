##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse
import sys
import time

from datetime import datetime, timedelta
from itertools import chain

import attr

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app import initialize_environment
from ..app.args import get_subparser
from ..cache import ConfigStatus, DeviceQuery

from .args import get_devargs_parser, MultiChoice


class ListDevice(object):
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        listp = get_subparser(
            subparsers,
            "list",
            description="List device configurations",
            parent=get_devargs_parser(),
        )
        listp.add_argument(
            "-u",
            dest="show_uid",
            default=False,
            action="store_true",
            help="Display ZODB path for device",
        )
        listp.add_argument(
            "-f",
            dest="states",
            action=MultiChoice,
            choices=("current", "retired", "expired", "pending", "building"),
            default=argparse.SUPPRESS,
            help="Only list configurations having these states.  One or "
            "more states may be specified, separated by commas.",
        )
        listp.set_defaults(factory=ListDevice)

    def __init__(self, args):
        self._monitor = args.collector
        self._service = args.service
        self._showuid = args.show_uid
        self._devices = getattr(args, "device", [])
        state_names = getattr(args, "states", ())
        if state_names:
            states = set()
            for name in state_names:
                states.add(_name_state_lookup[name])
            self._states = tuple(states)
        else:
            self._states = ()

    def run(self):
        haswildcard = any("*" in d for d in self._devices)
        if haswildcard and len(self._devices) > 1:
            print(
                "Only one DEVICE argument supported when a wildcard is used.",
                file=sys.stderr,
            )
            return
        initialize_environment(configs=self.configs, useZope=False)
        self._display(*self._collate(*self._get(haswildcard)))

    def _get(self, haswildcard):
        client = getRedisClient(url=getRedisUrl())
        store = createObject("deviceconfigcache-store", client)
        query = self._make_query(haswildcard)
        statuses = tuple(self._filter(store.query_statuses(query)))
        uid_map = self._get_uidmap(store, statuses)
        return (statuses, uid_map)

    def _collate(self, statuses, uid_map):
        rows = []
        maxd, maxs, maxt, maxa, maxm = 1, 1, 1, 1, 1
        now = time.time()
        for status in sorted(
            statuses, key=lambda x: (x.key.device, x.key.service)
        ):
            devid = (
                status.key.device
                if (status.key.device not in uid_map)
                else uid_map[status.key.device]
            )
            status_text = _format_status(status)
            ts = attr.astuple(status)[-1]
            ts_text = _format_date(ts)
            age_text = _format_timedelta(now - ts)
            maxd = max(maxd, len(devid))
            maxs = max(maxs, len(status_text))
            maxt = max(maxt, len(ts_text))
            maxa = max(maxa, len(age_text))
            maxm = max(maxm, len(status.key.monitor))
            rows.append(
                (
                    devid,
                    status_text,
                    ts_text,
                    age_text,
                    status.key.monitor,
                    status.key.service,
                )
            )
        return rows, (maxd, maxs, maxt, maxa, maxm)

    def _display(self, rows, widths):
        if rows:
            print(_header_template.format(*chain(_headings, widths)))
        for row in rows:
            print(_row_template.format(*chain(row, widths)))

    def _make_query(self, haswildcard):
        if haswildcard or len(self._devices) == 1:
            return DeviceQuery(
                service=self._service,
                monitor=self._monitor,
                device=self._devices[0],
            )
        return DeviceQuery(service=self._service, monitor=self._monitor)

    def _filter(self, data):
        if self._states:
            data = (
                status for status in data if isinstance(status, self._states)
            )
        if len(self._devices) > 1:
            data = (
                status for status in data if status.key.device in self._devices
            )
        return data

    def _get_uidmap(self, store, data):
        if self._showuid:
            deviceids = tuple(status.key.device for status in data)
            uids = store.get_uids(*deviceids)
            return dict(uids)
        return {}


_header_template = "{0:{6}}  {1:{7}}  {2:^{8}}  {3:^{9}}  {4:{10}}  {5}"
_row_template = "{0:{6}}  {1:{7}}  {2:{8}}  {3:>{9}}  {4:{10}}  {5}"
_headings = ("DEVICE", "STATUS", "LAST CHANGE", "AGE", "COLLECTOR", "SERVICE")

_name_state_lookup = {
    "current": ConfigStatus.Current,
    "retired": ConfigStatus.Retired,
    "expired": ConfigStatus.Expired,
    "pending": ConfigStatus.Pending,
    "building": ConfigStatus.Building,
}


def _format_timedelta(value):
    td = timedelta(seconds=value)
    hours = td.seconds // 3600
    minutes = (td.seconds - (hours * 3600)) // 60
    seconds = td.seconds - (hours * 3600) - (minutes * 60)
    return "{0} {1:02}:{2:02}:{3:02}".format(
        (
            ""
            if td.days == 0
            else "{} day{}".format(td.days, "" if td.days == 1 else "s")
        ),
        hours,
        minutes,
        seconds,
    ).strip()


def _format_status(status):
    return type(status).__name__.lower()


def _format_date(ts):
    when = datetime.fromtimestamp(ts)
    return when.strftime("%Y-%m-%d %H:%M:%S")
