##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import warnings
warnings.warn("TerminalServer is deprecated", DeprecationWarning)
from Device import Device

class TerminalServer(Device):
    def getRRDTemplateName(self):
        return "Device"
