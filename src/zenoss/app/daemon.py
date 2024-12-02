##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import argparse


class Daemon(object):
    def __init__(self, wrapped, configfile=None):
        self._wrapped = wrapped
        self._configfile = configfile
        self._parser = argparse.ArgumentParser(add_help=False)
        subparsers = self._parser.add_subparsers()

        self._helpp = subparsers.add_parser(
            "help", help="Print this message", add_help=False
        )
        self._helpp.set_defaults(func=self._help)

        runp = subparsers.add_parser(
            "run", help="Run the command", add_help=False
        )
        runp.set_defaults(func=run)

        # stopp = subparsers.add_parser("stop")
        # stopp.set_defaults(func=stop)

        genconfp = subparsers.add_parser(
            "genconf",
            help="Generate an example config file for this command",
            add_help=False,
        )
        genconfp.set_defaults(func=genconf)

        # statusp = subparsers.add_parser("status")
        # statusp.set_defaults(func=status)

        debugp = subparsers.add_parser("debug", add_help=False)
        debugp.set_defaults(func=debug)

        statsp = subparsers.add_parser("stats", add_help=False)
        statsp.set_defaults(func=stats)

    def main(self):
        args, remaining = self._parser.parse_known_args()
        args.func(self._wrapped, self._configfile, remaining)

    def _help(self, wrapped, configfile, args):
        self._parser.print_help()


def run(wrapped, configfile, args):
    wrapped.inputArgs = args
    if configfile:
        wrapped.inputArgs.extend(["-C", configfile])
    wrapped().run()


# def stop(wrapped, configfile, args):
#     wrapped.inputArgs = args
#     if configfile:
#         wrapped.inputArgs.extend(["-C", configfile])
#     wrapped().stop()


def genconf(wrapped, configfile, args):
    wrapped.inputArgs = ["--genconf"]
    wrapped().run()


def debug(wrapped, configfile, args):
    print("debugging")
    print(wrapped, configfile, args)


def stats(wrapped, configfile, args):
    print("stats")
    print(wrapped, configfile, args)
