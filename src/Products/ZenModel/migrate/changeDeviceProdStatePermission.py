##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
import logging
from Products.ZenModel.ZenossSecurity import *

class ChangeDeviceProdStatePermission(Migrate.Step):
    """
    The ZEN_CHANGE_DEVICE_PRODSTATE (Change Device Production State) permission
    has been added to Zenoss 2.5. This migrate script is used to update the
    appropriate menu item permissions for upgraded systems.
    """

    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        zport = dmd.zport
        if ZEN_CHANGE_DEVICE_PRODSTATE not in zport.possible_permissions():
            zport.__ac_permissions__ = (
                zport.__ac_permissions__ + ((ZEN_CHANGE_DEVICE_PRODSTATE, (),
                    [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE]),))

        m = dmd.zenMenus
        m.Device_list.zenMenuItems.setProductionState.permissions = \
                (ZEN_CHANGE_DEVICE_PRODSTATE,)
        m.DeviceGrid_list.zenMenuItems.setProductionState_grid.permissions = \
                (ZEN_CHANGE_DEVICE_PRODSTATE,)
        m.Edit.zenMenuItems.setProductionState.permissions = \
                (ZEN_CHANGE_DEVICE_PRODSTATE,)


changeDeviceProdStatePermission = ChangeDeviceProdStatePermission()
