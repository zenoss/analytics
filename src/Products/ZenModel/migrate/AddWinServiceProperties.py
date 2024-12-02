##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
Denormalizes serviceName and caption WinService properties to avoid loading
entire service class objects for common operations.
"""
import Migrate


class AddWinServiceProperties(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for b in dmd.Devices.componentSearch(meta_type='WinService'):
            service = b.getObject()
            serviceClass = service.serviceclass()
            if serviceClass:
                service.serviceName = serviceClass.name
                service.caption = serviceClass.description


AddWinServiceProperties()
