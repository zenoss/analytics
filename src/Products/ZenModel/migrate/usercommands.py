##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add usercommands to all device organizers, OsProcesses, Services, etc
Add some built-in commands

$Id:$
'''
import Migrate

class UserCommands(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        dmd.buildRelations()
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for name in ['Devices', 'Systems', 'Groups', 'Locations',
                        'Services', 'Processes']:
            top = getattr(dmd, name)
            orgs = top.getSubOrganizers()
            orgs.insert(0, top)
            for o in orgs:
                o.buildRelations()
                if name == 'Devices':
                    for d in o.devices():
                        d.buildRelations()
                        if getattr(d, 'os', None):
                            for n in ['ipservices', 'winservices', 'processes']:
                                for p in getattr(d.os, n)():
                                    p.buildRelations()
                if name == 'Services':
                    for sc in o.serviceclasses():
                        sc.buildRelations()
                if name == 'Processes':
                    for pc in o.osProcessClasses():
                        pc.buildRelations()

        # Add built-in commands
        commands = (('ping', 'ping -c2 ${device/manageIp}'),
                    ('traceroute', 'traceroute -q 1 -w 2 ${device/manageIp}'),
                    ('DNS forward', 'host ${device/id}'),
                    ('DNS reverse', 'host ${device/manageIp}'),
                    ('snmpwalk', 'snmpwalk -v1 -c${device/zSnmpCommunity}'
                                   ' ${here/manageIp} system'),
                    )
        commands = [c for c in commands 
                    if c[0] not in [d.id for d in dmd.userCommands()]]
        for id,cmd in commands:
            dmd.manage_addUserCommand(id, cmd=cmd)

UserCommands()
