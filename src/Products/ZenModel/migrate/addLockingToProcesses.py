############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

"""
Adds locking zproperties to the osprocess classes and organizers. 
"""

import Migrate
from Acquisition import aq_base
from Products.ZenModel.Lockable import UNLOCKED


class addLockingToProcesses(Migrate.Step):

    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        p = dmd.Processes
        if not hasattr(aq_base(p), "zModelerLock"): 
            p._setProperty("zModelerLock", UNLOCKED, type="int")
        if not hasattr(aq_base(p), "zSendEventWhenBlockedFlag"):
            p._setProperty("zSendEventWhenBlockedFlag", False, type="boolean")

addLockingToProcesses()
