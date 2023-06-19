##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Move the perf data out of the category-based directories and into a
single namespace.

'''

__version__ = "$Revision$"[11:-2]


import Migrate

import os

class HoistPerfData(Migrate.Step):
    version = Migrate.Version(0, 21, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.renames = []

    def cutover(self, dmd):
        names = dmd.getDmdRoot('Devices').getOrganizerNames(True)
        
        from Products.ZenUtils.path import zenPath
        oldbase = zenPath('perf', 'Devices')
        names.sort()
        names.reverse()
        for name in names:
            if name and name != '/':
                name = name.lstrip('/')
                root = os.path.join(oldbase, name, "devices")
                try:
                    for f in os.listdir(root):
                        oldname = os.path.join(root, f)
                        newname = os.path.join(oldbase, f)
                        if os.path.isdir(newname): continue
                        os.renames(oldname, newname)
                        self.renames.append( (oldname, newname) )
                except OSError as err:
                    import errno
                    n, msg = err.args
                    if n != errno.ENOENT:
                        raise err

    def revert(self):
        for oldname, newname in self.renames:
            os.renames(newname, oldname)

HoistPerfData()
