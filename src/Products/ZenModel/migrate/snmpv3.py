##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='Add zProperties for SNMPv3'

import Migrate
from Acquisition import aq_base

class SNMPv3(Migrate.Step):
    version = Migrate.Version(2, 1, 1)
    
    def cutover(self, dmd):
        devs = dmd.Devices
        for name in ("zSnmpSecurityName",
                     "zSnmpAuthPassword",
                     "zSnmpPrivPassword",
                     "zSnmpAuthType",
                     "zSnmpPrivType"):
            if not hasattr(aq_base(devs), name):
                devs._setProperty(name, "")

SNMPv3()
