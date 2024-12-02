##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Switch from one big component catalog to one per device
"""

from Products.ZenModel.migrate import Migrate


class perDeviceCompCatalog(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        # Delete the old componentSearch
        if dmd.Devices.hasObject('componentSearch'):
            dmd.Devices._delObject('componentSearch')

        # Reindex components in the new per-device catalogs
        for device in dmd.Devices.getSubDevicesGen():
            if not device.hasObject('componentSearch'):
                device._create_componentSearch()

perDeviceCompCatalog()
