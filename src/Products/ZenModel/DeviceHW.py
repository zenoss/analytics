##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Hardware import Hardware

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from Exceptions import *


class DeviceHW(Hardware):

    __pychecker__='no-override'

    meta_type = "DeviceHW"

    totalMemory = 0

    _properties = Hardware._properties + (
        {'id':'totalMemory', 'type':'long', 'mode':'w'},
    )

    _relations = Hardware._relations + (
        ("cpus", ToManyCont(ToOne, "Products.ZenModel.CPU", "hw")),
        ("cards", ToManyCont(ToOne, "Products.ZenModel.ExpansionCard", "hw")),
        ("harddisks", ToManyCont(ToOne, "Products.ZenModel.HardDisk", "hw")),
        ("fans", ToManyCont(ToOne, "Products.ZenModel.Fan", "hw")),
        ("powersupplies", ToManyCont(ToOne, "Products.ZenModel.PowerSupply",
            "hw")),
        ("temperaturesensors", ToManyCont(ToOne,
            "Products.ZenModel.TemperatureSensor", "hw")),
    )

    security = ClassSecurityInfo()

    def __init__(self):
        id = "hw"
        Hardware.__init__(self, id)

    
    def __call__(self, REQUEST=None):
        pp = self.getPrimaryParent()
        screen = getattr(pp, "deviceHardwareDetail", False)
        if not screen: return pp()
        return screen()

    def totalMemoryString(self):
        return self.totalMemory and convToUnits(self.totalMemory) or 'Unknown' 

    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()



InitializeClass(DeviceHW)
