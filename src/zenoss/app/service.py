##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from .command import Command


class Service(Command):
    def __init__(self, wrapped, configfile=None):
        super(Service, self).__init__(wrapped, configfile=configfile)

        debugp = self._command_parsers.add_parser(
            "debug",
            help="Toggle logging between DEBUG and the default",
            add_help=False,
        )
        debugp.set_defaults(func=debug)

        statsp = self._command_parsers.add_parser(
            "stats",
            help="Display detailed statistics of the running service",
            add_help=False,
        )
        statsp.set_defaults(func=stats)


def debug(wrapped, configfile, args):
    print("debugging")
    print(wrapped, configfile, args)


def stats(wrapped, configfile, args):
    print("stats")
    print(wrapped, configfile, args)
