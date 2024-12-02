##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add Mibs organizer and friends.

'''

__version__ = "$Revision$"[11:-2]

import Migrate

class Mibs(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
        if hasattr(dmd, 'Mibs'):
            return

        from Testing.ZopeTestCase.ZopeLite import installProduct
        installProduct('PluginIndexes', 1)

        from Products.ZenModel.MibOrganizer import manage_addMibOrganizer
        manage_addMibOrganizer(dmd, 'Mibs')

Mibs()
