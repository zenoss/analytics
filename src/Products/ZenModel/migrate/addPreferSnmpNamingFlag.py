##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zPreferSnmpNamingFlag z property.  If True, discovered devices will
use the snmp name (if found) instead of the dns name

$Id:$
'''
import Migrate
import transaction

class addPreferSnmpNamingFlag(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        if not hasattr( dmd.Networks, 'zPreferSnmpNaming' ):
            dmd.Networks._setProperty( 'zPreferSnmpNaming', False,'boolean')
            transaction.commit()


addPreferSnmpNamingFlag()
