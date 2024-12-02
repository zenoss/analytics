##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Creates root node from where triggers will be managed."""

import Migrate
from Products.ZenModel.Trigger import TriggerManager, manage_addTriggerManager
from Products.Zuul.utils import safe_hasattr as hasattr

class Triggers(Migrate.Step):
    version = Migrate.Version(4,0,0)

    def cutover(self, dmd):
        if not hasattr(dmd, TriggerManager.root):
            manage_addTriggerManager(dmd)

triggers = Triggers()
