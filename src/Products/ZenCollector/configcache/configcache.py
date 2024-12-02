##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from .app.args import get_arg_parser
from .cli import OidMap, Device
from .invalidator import Invalidator
from .manager import Manager
from .version import Version


def main(argv=None):
    parser = get_arg_parser("configcache commands")

    subparsers = parser.add_subparsers(title="Commands")

    Version.add_arguments(parser, subparsers)
    Manager.add_arguments(parser, subparsers)
    Invalidator.add_arguments(parser, subparsers)
    OidMap.add_arguments(parser, subparsers)
    Device.add_arguments(parser, subparsers)

    args = parser.parse_args()
    args.factory(args).run()
