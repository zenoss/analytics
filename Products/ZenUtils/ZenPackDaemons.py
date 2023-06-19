##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """zenpackdaemons
Manage ZenPack-provided daemons
"""

import os

from Products.ZenUtils.PkgResources import pkg_resources

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.ZenPackCmd import ZENPACK_ENTRY_POINT
from Products.ZenModel.ZenPackLoader import ZPLDaemons
from Products.ZenUtils.path import zenPath


class ZenPackDaemons(ZenScriptBase):
    """
    Utilities for handling ZenPack-provided daemons
    """

    def nameZenPackDaemons(self, zenPackId=None):
        """
        Return a list of the names of the daemons provided by the given ZenPack.  
        If no ZenPack is specified then list all daemons provided by all ZenPacks.
        """
        dList = []
        zpl = ZPLDaemons()
        # Get daemons from egg-based ZenPacks
        for entry in pkg_resources.iter_entry_points(ZENPACK_ENTRY_POINT):
            try:
                module = entry.load()
                dList += zpl.list(os.path.dirname(module.__file__), None)
            except Exception as ex:
                self.log.exception(
                    "The ZenPack %s cannot be imported -- skipping.", entry.name
                )

        # Get daemons from non-egg ZenPacks
        prodDir = zenPath('Products')
        for item in os.listdir(prodDir):
            if not item.startswith('.'):
                dList += zpl.list(os.path.join(prodDir, item), None)
        return dList


    def run(self):
        """
        Execute the user's request.
        """

        if self.options.list:
            dList = self.nameZenPackDaemons()
            if dList:
                print '\n'.join(dList)
        else:
            self.parser.print_help()


    def buildOptions(self):
        self.parser.add_option('--list',
                               dest='list',
                               default=False,
                               action='store_true',
                               help='List the names of ZenPack-supplied daemons'
                               )
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    zp = ZenPackDaemons()
    zp.run()
