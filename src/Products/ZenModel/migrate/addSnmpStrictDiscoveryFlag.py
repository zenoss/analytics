##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
Add zSnmpStrictDiscovery Z property.  If True, discoverDevices will not create
new devices for found IP's unless they return SNMP info
'''

import Migrate
import transaction

class addSnmpStrictDiscoveryFlag(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        # Quick sanity check
        props = dmd.Networks.zenPropertyIds()
        if 'zSnmpStrictDiscovery' in props:
            return

        dmd.Networks._setProperty('zSnmpStrictDiscovery',False,'boolean')
        transaction.commit()


addSnmpStrictDiscoveryFlag()
