##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.ServiceClass import ServiceClass


STARTMODE_AUTO = 'Auto'
STARTMODE_MANUAL = 'Manual'
STARTMODE_DISABLED = 'Disabled'
STARTMODE_NOTINSTALLED = 'Not Installed'


class WinServiceClass(ServiceClass):
    """
    Extends ServiceClass to add properties specific to Windows services.
    """

    monitoredStartModes = [STARTMODE_AUTO]

    _properties = ServiceClass._properties + (
        {'id': 'monitoredStartModes', 'type':'lines', 'mode':'rw'},
        )

    factory_type_information = ({
        'id'             : 'WinServiceClass',
        'meta_type'      : 'WinServiceClass',
        'icon'           : 'WinServiceClass.gif',
        'product'        : 'ZenModel',
        'factory'        : 'manage_addWinServiceClass',
        'immediate_view' : 'winServiceClassStatus',
        'actions': (
            { 'id'          : 'status'
            , 'name'        : 'Status'
            , 'action'      : 'winServiceClassStatus'
            , 'permissions' : (ZEN_VIEW,),
            },
            { 'id'          : 'edit'
            , 'name'        : 'Edit'
            , 'action'      : 'winServiceClassEdit'
            , 'permissions' : (ZEN_MANAGE_DMD,),
            },
            { 'id'          : 'manage'
            , 'name'        : 'Administration'
            , 'action'      : 'serviceClassManage'
            , 'permissions' : (ZEN_MANAGE_DMD,)
            },
            { 'id'          : 'zproperties'
            , 'name'        : 'Configuration Properties'
            , 'action'      : 'zPropertyEdit'
            , 'permissions' : (ZEN_CHANGE_DEVICE,)
            },
            ),
        },)

    security = ClassSecurityInfo()


    def manage_editServiceClass(self, name="", monitor=False,
        serviceKeys="", port=0, description="", monitoredStartModes=[],
        REQUEST=None):
        """
        Edit a WinServiceClass.
        """
        if self.monitoredStartModes != monitoredStartModes:
            self.monitoredStartModes = monitoredStartModes
            for inst in self.instances():
                inst._p_changed = True

        return super(WinServiceClass, self).manage_editServiceClass(
            name, monitor, serviceKeys, port, description, REQUEST)


InitializeClass(WinServiceClass)
