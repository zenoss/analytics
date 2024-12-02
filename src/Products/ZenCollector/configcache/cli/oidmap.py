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

from .expire import ExpireOidMap
from .show import ShowOidMap
from .stats import StatsOidMap


class OidMap(object):
    description = "Manage the OID Map cache"

    @staticmethod
    def add_arguments(parser, subparsers):
        oidmapp = get_subparser(
            subparsers,
            "oidmap",
            description=OidMap.description,
        )
        oidmap_subparsers = oidmapp.add_subparsers(title="OidMap Subcommands")
        ExpireOidMap.add_arguments(oidmapp, oidmap_subparsers)
        ShowOidMap.add_arguments(oidmapp, oidmap_subparsers)
        StatsOidMap.add_arguments(oidmapp, oidmap_subparsers)
