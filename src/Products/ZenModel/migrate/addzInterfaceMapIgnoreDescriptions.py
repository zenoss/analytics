##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zInterfaceMapIgnoreDescriptions zProperty.  This allows interfaces to be
ignored when modeled if their description matches this regex.
'''
import Migrate


class addzInterfaceMapIgnoreDescriptions(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if not hasattr( dmd.Devices, 'zInterfaceMapIgnoreDescriptions' ):
            dmd.Devices._setProperty('zInterfaceMapIgnoreDescriptions', '', 'string')

addzInterfaceMapIgnoreDescriptions()
