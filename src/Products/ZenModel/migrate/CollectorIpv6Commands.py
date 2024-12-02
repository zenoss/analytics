##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
This makes all of the user commands run on the collector of the
device.
This also sets the commands for Ping and SNMPWalk to work
for both Ipv6 and Ipv4
"""
import Migrate


class CollectorIpv6Commands(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        # ping ipv6
        try:
            ping = dmd.userCommands._getOb('ping')
            ping.command = "${device/pingCommand} -c2 ${device/manageIp}"
        except AttributeError:
            pass

        # traceroute
        try:
            traceroute = dmd.userCommands._getOb('traceroute')
            traceroute.command = "${device/tracerouteCommand} -q 1 -w 2 ${device/manageIp}"
        except AttributeError:
            pass

        # snmpwalk
        try:
            snmpwalk = dmd.userCommands._getOb('snmpwalk')
            snmpwalk.command = "snmpwalk -${device/zSnmpVer} -c${device/zSnmpCommunity} ${device/snmpwalkPrefix}${here/manageIp} system"
        except AttributeError:
            pass

        # make all of the default commands work over different collectors
        commands = ['ping', 'traceroute',
                    'DNS forward',
                    'DNS reverse',
                    'snmpwalk']
        for commandName in commands:
            try:
                cmd = dmd.userCommands._getOb(commandName)
                if not cmd.command.startswith('dcsh'):
                    cmd.command = 'dcsh --collector=${device/getPerformanceServerName} -n "%s"' % (cmd.command)
            except AttributeError:
                pass


CollectorIpv6Commands()
