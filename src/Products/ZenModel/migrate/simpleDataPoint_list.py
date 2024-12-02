##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class SimpleDataPoint_list(Migrate.Step):

    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        dmd.buildMenus(dict(
            SimpleDataPoint_list=[dict(
                id='addDataPointsToGraphs',
                description='Add to Graphs...',
                action='dialog_addDataPointsToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0
            )]
        ))


SimpleDataPoint_list()
