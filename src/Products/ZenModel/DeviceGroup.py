##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""DeviceGroup


$Id: DeviceGroup.py,v 1.15 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable

def manage_addDeviceGroup(context, id, description = None, REQUEST = None):
    """make a DeviceGroup"""
    d = DeviceGroup(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 


addDeviceGroup = DTMLFile('dtml/addDeviceGroup',globals())



class DeviceGroup(DeviceOrganizer, ZenPackable):
    """
    DeviceGroup is a DeviceGroup Organizer that allows generic device groupings.
    """

    # Organizer configuration
    dmdRootName = "Groups"

    portal_type = meta_type = event_key = 'DeviceGroup'

    _relations = DeviceOrganizer._relations + ZenPackable._relations + (
        ("devices", ToMany(ToMany,"Products.ZenModel.Device","groups")),
        )

InitializeClass(DeviceGroup)
