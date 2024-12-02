##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

change attribute name in interface to interfaceName because it
conflicts with name function of DeviceClass

'''

__version__ = "$Revision$"[11:-2]

import Migrate

from Acquisition import aq_base


class InterfaceNameConvert(Migrate.Step):
    version = Migrate.Version(0, 21, 0)

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            for int in dev.os.interfaces():
                interfaceName = getattr(aq_base(int), 'name', None)
                if interfaceName is not None and not callable(interfaceName):
                    int.interfaceName = interfaceName
                    delattr(int, 'name')
        try:
            dmd.Devices.reIndex()
        except AttributeError:
            pass
        if hasattr(aq_base(dmd.Devices), "interfaceSearch"):
            dmd.Devices._delObject("interfaceSearch")


InterfaceNameConvert()
