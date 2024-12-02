##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate

from Products.ZenModel.ZenossSecurity import *

class LinuxSSHProperties(Migrate.Step):

    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        #Add devtypes for SSH.Linux
        dmd.Devices.Server.SSH.Linux.devtypes = [('Linux Server', 'SSH')]

        #Skip if we've already got it
        for prop in dmd.Devices.Server.SSH.Linux._properties:
            if prop['id'] == 'zIcon':
                return

        #Make zIcon consistent for the two Linux device classes
        for prop in dmd.Devices.Server.Linux._properties:
            if prop['id'] == 'zIcon':
                dmd.Devices.Server.SSH.Linux._properties += (prop,)
        dmd.Devices.Server.SSH.Linux.zIcon = dmd.Devices.Server.Linux.zIcon

LinuxSSHProperties()
