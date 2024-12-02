##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
Migrate snmpwalk command to specify port in order to perform snmpwalk on
non standard ports.
"""
import Migrate

_IP_WITHOUT_PORT = '${here/manageIp} system'
class SnmpWalkWithPort(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        # snmpwalk
        try:
            snmpwalk = dmd.userCommands._getOb('snmpwalk')
            if _IP_WITHOUT_PORT in snmpwalk.command:
                snmpwalk.command = snmpwalk.command.replace(_IP_WITHOUT_PORT, '${here/manageIp}:${here/zSnmpPort} system', 1)
        except AttributeError:
            pass

SnmpWalkWithPort()
