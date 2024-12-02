##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
'''
import Migrate

class DeviceHWRelations(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import twotwoindexing
        self.dependencies = [ twotwoindexing.twotwoindexing ]

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.hw.buildRelations()

DeviceHWRelations()
