##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate




class fixNmapArgsTemplate(Migrate.Step):
    " Update default args for nmap command "

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        
        if hasattr(dmd.Devices, 'zNmapPortscanOptions'): 
        	dmd.Devices.zNmapPortscanOptions = '-p 1-1024 -sT --open -oG -'



fixNmapArgsTemplate()
