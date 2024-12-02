##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse
import sys


class Command(object):
    def __init__(self, wrapped, configfile=None):
        self._wrapped = wrapped
        self._configfile = configfile
        self._parser = argparse.ArgumentParser(add_help=False)
        self._command_parsers = self._parser.add_subparsers(title="Commands")

        self._helpp = self._command_parsers.add_parser(
            "help", help="Print this message", add_help=False
        )
        self._helpp.set_defaults(func=self._help)

        runp = self._command_parsers.add_parser(
            "run", help="Run the command", add_help=False
        )
        runp.set_defaults(func=run)

        genconfp = self._command_parsers.add_parser(
            "genconf",
            help="Generate an example config file for this command",
            add_help=False,
        )
        genconfp.set_defaults(func=genconf)

    def main(self):
        args, remaining = self._parser.parse_known_args()
        args.func(self._wrapped, self._configfile, remaining)

    def _help(self, wrapped, configfile, args):
        self._parser.print_help()


def run(wrapped, configfile, args):
    if configfile:
        args = ["--configfile", configfile] + args
    sys.argv[1:] = args
    wrapped().run()


def genconf(wrapped, configfile, args):
    sys.argv[1:] = ["--genconf"]
    wrapped().run()
