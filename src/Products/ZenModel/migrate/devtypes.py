##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Set zRouteMapMaxRoutes defaults

$Id:$
'''
import Migrate
import zExceptions

class AddDeviceClassDescriptionAndProtocol(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):

        # Set values for some core organizers
        for path, desc, protocol in [
            ('/Server/Windows', 'Windows Server', 'SNMP'),
            ('/Server/Linux', 'Linux Server', 'SNMP'),
            ('/Network', 'Generic Switch/Router', 'SNMP'),
        ]:
            try:
                org = dmd.Devices.unrestrictedTraverse(path[1:])
            except KeyError:
                pass
            else:
                org.register_devtype(desc, protocol)


AddDeviceClassDescriptionAndProtocol()


class RegisterRootDevtype(Migrate.Step):
    """Register root devtype, to support propertyItems access at all device type levels."""
    version = Migrate.Version(3,1,0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty('devtypes'):
            dmd.Devices._setProperty('devtypes', [], 'lines')


RegisterRootDevtype()
