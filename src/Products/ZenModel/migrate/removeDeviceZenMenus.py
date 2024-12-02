##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
The "rename device" and "delete device" dialogs were rewritten in ExtJs so
remove them from the ZODB.
'''
__version__ = "$Revision$"[11:-2]

import Migrate

from Products.Zuul.utils import safe_hasattr as hasattr

class RemoveDeviceZenMenus(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        rel = dmd.zenMenus.Manage.zenMenuItems
        if hasattr(rel, 'deleteDevice'):
            rel._delObject('deleteDevice')
        if hasattr(rel, 'renameDevice'):
            rel._delObject('renameDevice')
        if hasattr(rel, 'lockObject'):
            rel._delObject('lockObject')


RemoveDeviceZenMenus()
