##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

remove zPingInterfaceName and zPingInterfaceDescription from everything.

'''
import Migrate

class zPingInterfacePropsDelete(Migrate.Step):
    version = Migrate.Version(2, 5, 0)
    
    def cutover(self, dmd):
        orgs = [dmd.Devices]
        orgs.extend(dmd.Devices.getSubOrganizers())
        for org in orgs:
            deleteZProp(org, 'zPingInterfaceName')
            deleteZProp(org, 'zPingInterfaceDescription')
        #now do devices; use generator
        for device in dmd.Devices.getSubDevicesGen():
            deleteZProp(device, 'zPingInterfaceName')
            deleteZProp(device, 'zPingInterfaceDescription')
        
def deleteZProp(obj, zProp):
        if obj.hasProperty(zProp):
            obj.deleteZenProperty(zProp)

zPingInterfacePropsDelete()
