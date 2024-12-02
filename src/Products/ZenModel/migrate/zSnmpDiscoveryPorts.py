##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

'''
Add zSnmpDiscoveryPorts to DeviceClass.
'''

import Migrate

class zSnmpDiscoveryPorts(Migrate.Step):
    version = Migrate.Version(4, 2, 70)
    
    def cutover(self, dmd):
        if not dmd.Devices.hasProperty('zSnmpDiscoveryPorts'):
            dmd.Devices._setProperty('zSnmpDiscoveryPorts',
                [], 'lines', 'SNMP ports that zendisc will search', True)

zSnmpDiscoveryPorts()
