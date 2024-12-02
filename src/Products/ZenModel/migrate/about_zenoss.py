##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Create the directories on the file system necessary for importing and exporting
templates to and from Zenoss.

'''

__version__ = "$Revision$"[11:-2]

from Products.ZenModel.ZenossInfo import manage_addZenossInfo

import Migrate

class AboutZenoss(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if hasattr(dmd.zport, 'ZenossInfo'):
            dmd.zport._delObject('ZenossInfo')
        if not hasattr(dmd,'About'):
            manage_addZenossInfo(dmd)

AboutZenoss()
