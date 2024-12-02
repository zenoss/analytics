##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zLinks to DeviceClass.

'''
import Migrate

class zIconProperty(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        if not dmd.Networks.hasProperty('zIcon'):
            dmd.Networks._setProperty(
                "zIcon", "/zport/dmd/img/icons/network.png")
        if not dmd.Devices.hasProperty('zIcon'):
            dmd.Devices._setProperty(
                "zIcon", "/zport/dmd/img/icons/noicon.png")
        try:
            if not dmd.Devices.Network.Router.hasProperty('zIcon'):
                dmd.Devices.Network.Router._setProperty(
                    "zIcon", "/zport/dmd/img/icons/router.png")
        except AttributeError: pass
        try:
            if not dmd.Devices.Server.hasProperty('zIcon'):
                dmd.Devices.Server._setProperty(
                    "zIcon", "/zport/dmd/img/icons/server.png")
        except AttributeError: pass
        try:
            if not dmd.Devices.Server.Windows.hasProperty('zIcon'):
                dmd.Devices.Server.Windows._setProperty(
                    "zIcon", "/zport/dmd/img/icons/server-windows.png")
        except AttributeError: pass
        try:
            if not dmd.Devices.Server.Linux.hasProperty('zIcon'):
                dmd.Devices.Server.Linux._setProperty(
                    "zIcon", "/zport/dmd/img/icons/server-linux.png")
        except AttributeError: pass
              


zIconProperty()
