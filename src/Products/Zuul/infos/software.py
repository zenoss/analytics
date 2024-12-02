
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.Zuul.infos import InfoBase
from Products.Zuul.decorators import info

class SoftwareInfo(InfoBase):
    """
    Although Software is a DeviceComponent, it doesn't behave like one in the ways ComponentInfo assumes, so we'll subclass InfoBase instead of ComponentInfo.
    """
    
    @property
    @info
    def manufacturer(self):
        return self._object.getManufacturer()

    @property
    def name(self):
        return self._object.getProductName()
        
    @property
    def namelink(self):
        return self._object.getProductHref()        
        
    @property
    def installdate(self):
        return self._object.getInstallDate()        

