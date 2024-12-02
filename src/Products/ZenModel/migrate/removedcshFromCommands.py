##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """
In a previous migrate script we wrapped the commands in a dcsh so that they would
run on any collector. This turned out to be a bad idea to place it in there because it
made localhost commands very slow.

Instead when running the command we look up the collector and wrap the command
in dcsh if necessary. See the ZenModel/Commandable.py "compile" method.
"""
import Migrate


class RemoveDCSHFromCommand(Migrate.Step):
    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        # make all of the default commands work over different collectors
        commands = ['ping', 'traceroute',
                    'DNS forward',
                    'DNS reverse',
                    'snmpwalk']
        for commandName in commands:
            try:
                cmd = dmd.userCommands._getOb(commandName)
                if cmd.command.startswith('dcsh --collector=${device/getPerformanceServerName} -n'):
                    cmd.command = cmd.command.replace("dcsh --collector=${device/getPerformanceServerName} -n ", "")
                    cmd.command = cmd.command.strip('"')
            except AttributeError:
                pass


RemoveDCSHFromCommand()
