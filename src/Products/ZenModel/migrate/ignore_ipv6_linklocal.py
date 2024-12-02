##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Add fe80:: to zLocalIpAddresses in DeviceClass.
"""

import Migrate


class IgnoreIPv6LinkLocal(Migrate.Step):
    version = Migrate.Version(4, 2, 4)

    def cutover(self, dmd):
        value = dmd.Devices.getZ("zLocalIpAddresses")
        if value and "^fe80::" not in value:
            value += "|^fe80::"
            dmd.Devices.setZenProperty("zLocalIpAddresses", value)

IgnoreIPv6LinkLocal()
