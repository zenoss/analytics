##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""
WinServiceClass is now a subclass of ServiceClass. We need to iterate over
all of the appropriate ServiceClasses in the system and convert them.
"""

import Migrate
from Products.ZenModel.WinServiceClass import WinServiceClass, STARTMODE_AUTO
from Products.ZenModel.ServiceClass import ServiceClass


class AddWinServiceClass(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for service_class in dmd.Services.WinService.getSubClassesGen():
            if service_class.__class__ == ServiceClass:
                service_class.__class__ = WinServiceClass
                service_class.monitoredStartModes = [STARTMODE_AUTO]


AddWinServiceClass()
