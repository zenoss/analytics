##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='Add zProperties for SNMPv3'

import Migrate
from Acquisition import aq_base

class snmpv3trap(Migrate.Step):
    version = Migrate.Version(4, 0, 0)
    
    def cutover(self, dmd):
        if not hasattr(aq_base(dmd.Devices), "zSnmpEngineId"):
            dmd.Devices._setProperty("zSnmpEngineId", "")

snmpv3trap()
