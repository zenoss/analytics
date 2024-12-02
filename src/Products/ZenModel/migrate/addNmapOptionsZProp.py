##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add a zProperty to allow for control of the nmap portscan plugin.

'''
import Migrate

class addNmapOptionsZProp(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        if not hasattr(dmd.Devices, 'zNmapPortscanOptions'):
            dmd.Devices._setProperty("zNmapPortscanOptions", "-p 1-1024;-sT;--open;-oG -")

addNmapOptionsZProp()
