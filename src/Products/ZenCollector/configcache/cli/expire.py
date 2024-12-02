##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import sys
import time

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app import initialize_environment
from ..app.args import get_subparser
from ..cache import ConfigStatus, DeviceQuery

from .args import get_devargs_parser
from ._selection import get_message, confirm


class ExpireOidMap(object):
    description = "Mark OID Map as expired"
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "expire",
            description=ExpireOidMap.description,
        )
        subp.set_defaults(factory=ExpireOidMap)

    def __init__(self, args):
        pass

    def run(self):
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("oidmapcache-store", client)
        status = store.get_status()
        if not isinstance(status, ConfigStatus.Expired):
            store.set_expired(time.time())
            print("Expired oidmap configuration")
        else:
            print("Oidmap configuration already expired")


class ExpireDevice(object):
    description = "Mark device configurations as expired"
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "expire",
            description=ExpireDevice.description,
            parent=get_devargs_parser(),
        )
        subp.set_defaults(factory=ExpireDevice)

    def __init__(self, args):
        self._monitor = args.collector
        self._service = args.service
        self._devices = getattr(args, "device", [])

    def run(self):
        haswildcard = any("*" in d for d in self._devices)
        if haswildcard:
            if len(self._devices) > 1:
                print(
                    "Only one DEVICE argument supported when a "
                    "wildcard is used.",
                    file=sys.stderr,
                )
                return
        if not self._confirm_inputs():
            print("exit")
            return
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("deviceconfigcache-store", client)
        self._expire(store, self._get(store, haswildcard))

    def _get(self, store, haswildcard):
        query = self._make_query(haswildcard)
        results = store.query_statuses(query)
        return tuple(self._get_keys_from_results(results, haswildcard))

    def _expire(self, store, keys):
        now = time.time()
        store.set_expired(*((key, now) for key in keys))
        count = len(keys)
        print(
            "expired %d device configuration%s"
            % (count, "" if count == 1 else "s")
        )

    def _make_query(self, haswildcard):
        if haswildcard:
            return DeviceQuery(
                service=self._service,
                monitor=self._monitor,
                device=self._devices[0],
            )
        return DeviceQuery(service=self._service, monitor=self._monitor)

    def _get_keys_from_results(self, results, haswildcard):
        if not self._devices or haswildcard:
            return (status.key for status in results)
        return (
            status.key
            for status in results
            if status.key.device in self._devices
        )

    def _confirm_inputs(self):
        if self._devices:
            return True
        mesg = get_message("Recreate", self._monitor, self._service)
        return confirm(mesg)
