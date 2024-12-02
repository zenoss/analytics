##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys as _sys

from .app.args import get_subparser


class Version(object):

    description = "Display the version and exit"

    @staticmethod
    def add_arguments(parser, subparsers):
        subp_version = get_subparser(
            subparsers, "version", description=Version.description
        )
        subp_version.set_defaults(factory=Version)

    def __init__(self, args):
        pass

    def run(self):
        from Products.ZenModel.ZenossInfo import ZenossInfo

        zinfo = ZenossInfo("")
        version = zinfo.getZenossVersion().short()
        print("{} {}".format(_app_name(), version))


def _app_name():
    fn = _sys.argv[0].rsplit("/", 1)[-1]
    return fn.rsplit(".", 1)[0] if fn.endswith(".py") else fn
