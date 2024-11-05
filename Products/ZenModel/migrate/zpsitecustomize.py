##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

'''
import Migrate
from Products.ZenUtils.path import zenPath

class zpSiteCustomize(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        # Write extra path to sitecustomize.py
        import sys
        if zenPath('ZenPacks') in sys.path: return
        path = zenPath('lib', 'python', 'sitecustomize.py')
        f = open(path, 'r')
        t = f.read()
        f.close()
        f = open(path, 'w')
        f.write(t)
        f.write('\nimport os, os.path, site; ')
        f.write("site.addsitedir(os.path.join(os.getenv('ZENHOME'), 'ZenPacks'))\n")
        f.close()

zpSiteCustomize()
