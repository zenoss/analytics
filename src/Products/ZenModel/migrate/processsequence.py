##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''ProcessSequence

Make sure OSProcesses are sequenced

'''
import Migrate

class ProcessSequence(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        dmd.Processes.getSubOSProcessClassesSorted()

ProcessSequence()
