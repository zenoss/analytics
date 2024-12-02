__doc__ = """
Add user snmpwalk command for snmp v3
"""

import Migrate

SNMPV3_ID = 'snmpwalk_v3'
SNMPV3_COMMAND = ('snmpwalk -${device/zSnmpVer} -l authNoPriv -a ${device/zSnmpAuthType} '
                  '-x ${device/zSnmpPrivType} -A ${device/zSnmpAuthPassword} '
                  '-X ${device/zSnmpPrivPassword} -u ${device/zSnmpSecurityName} '
                  '${device/snmpwalkPrefix}${here/manageIp}:${here/zSnmpPort} system')


class AddSnmpV3UserCommand(Migrate.Step):

    version = Migrate.Version(107, 0, 0)

    def cutover(self, dmd):
        if SNMPV3_ID not in [d.id for d in dmd.userCommands()]:
            dmd.manage_addUserCommand(SNMPV3_ID, cmd=SNMPV3_COMMAND)
        snmpwalk = dmd.userCommands._getOb(SNMPV3_ID)
        snmpwalk.description = 'snmp version v3: Display the OIDs available on a device'


AddSnmpV3UserCommand()

