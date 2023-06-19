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

import os

import Migrate

from Products.ZenUtils.path import zenPath

class ImportExportFilesystem(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, unused):
        for directory in ['import', 'export']:
            path = zenPath(directory)
            if not os.path.exists(path):
                os.mkdir(path, 0o750)

ImportExportFilesystem()
