##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from info import IInfo
from zope.interface import Attribute

class ISoftwareInfo(IInfo):
    manufacturer = Attribute("The software manufacturer with link to manufacturer page included")
    name = Attribute("The software name")
    namelink = Attribute("The uid link to the software page")
    installdate = Attribute("The install date of the software")
    pass 
