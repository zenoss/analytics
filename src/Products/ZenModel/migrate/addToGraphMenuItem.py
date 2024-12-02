##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class AddToGraphMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    

    def cutover(self, dmd):
        
        dsMenu = dmd.zenMenus._getOb('DataSource_list', None)
        if dsMenu and not dsMenu.zenMenuItems._getOb('addDataSourcesToGraphs', None):
            dsMenu.manage_addZenMenuItem(
                id='addDataSourcesToGraphs',
                description='Add to Graphs...',
                action='dialog_addDataSourcesToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0)

        dpMenu = dmd.zenMenus._getOb('DataPoint_list', None)
        if dpMenu and not dpMenu.zenMenuItems._getOb('addDataPointsToGraphs', None):
            dpMenu.manage_addZenMenuItem(
                id='addDataPointsToGraphs',
                description='Add to Graphs...',
                action='dialog_addDataPointsToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0)

        threshMenu = dmd.zenMenus._getOb('Threshold_list', None)
        if threshMenu and not threshMenu.zenMenuItems._getOb('addThresholdsToGraphs', None):
            threshMenu.manage_addZenMenuItem(
                id='addThresholdsToGraphs',
                description='Add to Graphs...',
                action='dialog_addThresholdsToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0)


AddToGraphMenuItem()
