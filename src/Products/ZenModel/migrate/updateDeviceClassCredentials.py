##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """Populates the credentialsZProperties property on the core device classes. This list of zproperties drives the credentials section of the device overview page."""


import Migrate
import logging

log = logging.getLogger( 'zen.migrate' )

class UpdateDeviceClassCredentials(Migrate.Step):
    version = Migrate.Version(5, 0, 0)


    def cutover(self, dmd):
        # network
        network = dmd.Devices.Network
        network.setZenProperty('zCredentialsZProperties', ['zSnmpCommunity'])

        # snmp
        server = dmd.Devices.Server
        server.setZenProperty('zCredentialsZProperties', ['zSnmpCommunity'])

        # SSH
        ssh = dmd.Devices.Server.SSH
        ssh.setZenProperty('zCredentialsZProperties', ['zCommandUsername', 'zCommandPassword'])

updateDeviceClassCredentials = UpdateDeviceClassCredentials()
