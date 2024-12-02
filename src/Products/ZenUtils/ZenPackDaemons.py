##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zenpackdaemons
Manage ZenPack-provided daemons
"""

from __future__ import absolute_import, print_function

import os

import pkg_resources

from Products.ZenModel.ZenPackLoader import ZPLDaemons

from .ZenScriptBase import ZenScriptBase


class ZenPackDaemons(ZenScriptBase):
    """
    Utilities for handling ZenPack-provided daemons
    """

    def nameZenPackDaemons(self, zenPackId=None):
        """
        Return a list of the names of the daemons provided by the given
        ZenPack.  If no ZenPack is specified then list all daemons provided
        by all ZenPacks.
        """
        from Products.ZenUtils.ZenPackCmd import ZENPACK_ENTRY_POINT
        dList = []
        zpl = ZPLDaemons()
        # Get daemons from egg-based ZenPacks
        for entry in pkg_resources.iter_entry_points(ZENPACK_ENTRY_POINT):
            try:
                module = entry.load()
                dList += zpl.list(os.path.dirname(module.__file__), None)
            except Exception:
                self.log.exception(
                    "The ZenPack %s cannot be imported -- skipping.",
                    entry.name,
                )
        return dList

    def run(self):
        """
        Execute the user's request.
        """
        if self.options.list:
            dList = self.nameZenPackDaemons()
            if dList:
                print("\n".join(dList))
        else:
            self.parser.print_help()

    def buildOptions(self):
        self.parser.add_option(
            "--list",
            dest="list",
            default=False,
            action="store_true",
            help="List the names of ZenPack-supplied daemons",
        )
        ZenScriptBase.buildOptions(self)


def main():
    ZenPackDaemons().run()
