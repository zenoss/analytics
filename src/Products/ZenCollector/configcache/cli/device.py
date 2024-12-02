##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from ..app.args import get_subparser

from .expire import ExpireDevice
from .list import ListDevice
from .remove import RemoveDevice
from .show import ShowDevice
from .stats import StatsDevice


class Device(object):
    description = "Manage the device configuration cache"

    @staticmethod
    def add_arguments(parser, subparsers):
        devicep = get_subparser(
            subparsers,
            "device",
            description=Device.description,
        )
        device_subparsers = devicep.add_subparsers(title="Device Subcommands")
        ExpireDevice.add_arguments(devicep, device_subparsers)
        ListDevice.add_arguments(devicep, device_subparsers)
        RemoveDevice.add_arguments(devicep, device_subparsers)
        ShowDevice.add_arguments(devicep, device_subparsers)
        StatsDevice.add_arguments(devicep, device_subparsers)
