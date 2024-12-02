##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds AccountLocker plugin to PAS.
''' 

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import os
from Products.ZenUtils.AccountLocker.AccountLocker import setup


class AddAccountLocker(Migrate.Step):

    version = Migrate.Version(109, 0, 0)

    def cutover(self, dmd):
        
        setup(dmd)
        log.info("Account locker is installed.")

AddAccountLocker()
