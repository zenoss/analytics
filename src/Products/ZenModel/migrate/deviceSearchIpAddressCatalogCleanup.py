##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
Migrate script that removes extra indexes that we do not need to catalog
to save time when cataloging devices and ip addresses
'''

__version__ = "$Revision$"[11:-2]

from Products.ZCatalog.Catalog import CatalogError
import Migrate

deviceSearchIndexes = ['getHWSerialNumber', 'getHWTag',
                       'getHWManufacturerName', 'getHWProductClass',
                       'getOSProductName', 'getOSManufacturerName',
                       'getPerformanceServerName', 'ipAddressAsInt',
                       'getProductionStateString', 'getPriorityString',
                       'getLocationName', 'getSystemNames', 'getDeviceGroupNames', 'allowedRolesAndUsers']


ipAddressIndexes = ['getInterfaceName', 'getDeviceName',
                    'getInterfaceDescription', 'getInterfaceMacAddress', 'allowedRolesAndUsers']

class DeviceSearchIpAddressCatalogCleanup(Migrate.Step):

    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        # device search
        cat = dmd.Devices.deviceSearch._catalog
        try:
            cat.delColumn('details')
        except ValueError:
            # already removed
            pass
        # remove
        for idx in deviceSearchIndexes:
            try:
                cat.delIndex(idx)
            except CatalogError:
                # already removed
                pass

        # networks
        for cat in (dmd.Networks.ipSearch._catalog, dmd.IPv6Networks.ipSearch._catalog):
            try:
                cat.delColumn('details')
            except ValueError:
                # already removed
                pass

            # remove indexes
            for idx in ipAddressIndexes:
                try:
                    cat.delIndex(idx)
                except CatalogError:
                    # already removed
                    pass

DeviceSearchIpAddressCatalogCleanup()
