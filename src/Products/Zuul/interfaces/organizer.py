##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from info import IInfo
from zope.interface import Attribute

class IOrganizerInfo(IInfo):
    """
    Organizer info
    """

class ILocationOrganizerInfo(IOrganizerInfo):
    """
    Location info
    """
    address = Attribute('The address of the organizer')

class IDeviceClassInfo(IOrganizerInfo):
    pass
