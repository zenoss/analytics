##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import os
import sys
import types

from IPython.lib import pretty
from twisted.spread.jelly import unjellyableRegistry
from twisted.spread import pb
from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.ZenUtils.terminal_size import get_terminal_size

from ..app import initialize_environment
from ..app.args import get_subparser
from ..cache import DeviceQuery


class ShowOidMap(object):
    description = "Show the oidmap configuration"
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "show",
            description=ShowOidMap.description,
        )
        termsize = get_terminal_size()
        subp.add_argument(
            "--width",
            type=int,
            default=termsize.columns,
            help="Maxiumum number of columns to use in the output. "
            "By default, this is the width of the terminal",
        )
        subp.set_defaults(factory=ShowOidMap)

    def __init__(self, args):
        if _is_output_redirected():
            # when stdout is redirected, default to 79 columns unless
            # the --width option has a non-default value.
            termsize = get_terminal_size()
            if args.width != termsize.columns:
                self._columns = args.width
            else:
                self._columns = 79
        else:
            self._columns = args.width

    def run(self):
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("oidmapcache-store", client)
        record = store.get()
        if record is None:
            print(
                "No oidmap configuration found in the cache", file=sys.stderr
            )
        else:
            pretty.pprint(
                record.oidmap, max_width=self._columns, max_seq_length=0
            )


class ShowDevice(object):
    description = "Show a device configuration"
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers, "show", description=ShowDevice.description
        )
        termsize = get_terminal_size()
        subp.add_argument(
            "--width",
            type=int,
            default=termsize.columns,
            help="Maxiumum number of columns to use in the output. "
            "By default, this is the width of the terminal",
        )
        subp.add_argument(
            "service", nargs=1, help="name of the configuration service"
        )
        subp.add_argument(
            "collector", nargs=1, help="name of the performance collector"
        )
        subp.add_argument("device", nargs=1, help="name of the device")
        subp.set_defaults(factory=ShowDevice)

    def __init__(self, args):
        self._monitor = args.collector[0]
        self._service = args.service[0]
        self._device = args.device[0]
        if _is_output_redirected():
            # when stdout is redirected, default to 79 columns unless
            # the --width option has a non-default value.
            termsize = get_terminal_size()
            if args.width != termsize.columns:
                self._columns = args.width
            else:
                self._columns = 79
        else:
            self._columns = args.width

    def run(self):
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("deviceconfigcache-store", client)
        results, err = _query_cache(
            store,
            service=self._service,
            monitor=self._monitor,
            device=self._device,
        )
        if results:
            for cls in set(unjellyableRegistry.values()):
                if isinstance(
                    cls, (types.ClassType, types.TypeType)
                ) and issubclass(cls, (pb.Copyable, pb.RemoteCopy)):
                    pretty.for_type(cls, _pp_hide_passwords)
                else:
                    pretty.for_type(cls, _pp_default)
            try:
                pretty.pprint(
                    results.config, max_width=self._columns, max_seq_length=0
                )
            except IOError as ex:
                if ex.errno != 32:  # broken pipe
                    print(ex, file=sys.stderr)
            except KeyboardInterrupt as ex:
                print(ex, file=sys.stderr)
        else:
            print(err, file=sys.stderr)


def _query_cache(store, service, monitor, device):
    query = DeviceQuery(service=service, monitor=monitor, device=device)
    results = store.search(query)
    first_key = next(results, None)
    if first_key is None:
        return (None, "device configuration not found")
    second_key = next(results, None)
    if second_key is not None:
        return (None, "more than one device configuration matched arguments")
    return (store.get(first_key), None)


def _pp_hide_passwords(obj, p, cycle):
    _printer(
        obj,
        p,
        cycle,
        lambda k, v: v if "password" not in k.lower() else "******",
    )


def _pp_default(obj, p, cycle):
    _printer(obj, p, cycle, lambda k, v: v)


def _printer(obj, p, cycle, vprint):
    clsname = obj.__class__.__name__
    if cycle:
        p.text("<{}: ...>".format(clsname))
    else:
        with p.group(2, "<{}: ".format(clsname), ">"):
            attrs = (
                (k, v)
                for k, v in sorted(obj.__dict__.items(), key=lambda x: x[0])
                if v not in (None, "", {}, [])
            )
            for idx, (k, v) in enumerate(attrs):
                if idx:
                    p.text(",")
                    p.breakable()
                p.text("{}=".format(k))
                p.pretty(vprint(k, v))


def _is_output_redirected():
    return os.fstat(0) != os.fstat(1)
