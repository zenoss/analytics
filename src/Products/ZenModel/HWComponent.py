##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Hardware import Hardware
from DeviceComponent import DeviceComponent


class HWComponent(DeviceComponent, Hardware):
    """
    Hardware component of a device such as a HardDisk, CPU, etc.
    """

    def device(self):
        """Return our device object for DeviceResultInt.
        """
        hw = self.hw()
        if hw: return hw.device()
