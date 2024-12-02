##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class OSProcessMemoryBase1024(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        try:
            g = dmd.Devices.rrdTemplates.OSProcess.graphDefs.Memory
            g.base = True
        except AttributeError:
            # We don't care of the OSProcess tempalte doesn't exist. We also
            # don't care if the Memory graph doesn't exist.
            pass

osProcessMemoryBase1024 = OSProcessMemoryBase1024()
