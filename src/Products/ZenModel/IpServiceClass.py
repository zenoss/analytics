##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass

from AccessControl import Permissions
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import *

from Products.ZenRelations.RelSchema import *

from ServiceClass import ServiceClass


def manage_addIpServiceClass(context, id, REQUEST = None):
    """make a device"""
    ipsc = IpServiceClass(id)
    context._setObject(ipsc.id, ipsc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main') 
    return ipsc.id


addIpServiceClass = DTMLFile('dtml/addIpServiceClass',globals())

class IpServiceClass(ServiceClass):
    """IpServiceClass object.
    """
    __pychecker__='no-override'

    sendString = ""
    expectRegex = ""

    portal_type = meta_type = 'IpServiceClass'

    _properties = ServiceClass._properties + (
        {'id':'sendString', 'type':'string', 'mode':'w'},
        {'id':'expectRegex', 'type':'string', 'mode':'w'},
        )

    factory_type_information = (
        { 
            'immediate_view' : 'ipServiceClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'ipServiceClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'ipServiceClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'ipServiceClassManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, serviceKeys=(), description="", port=0):
        ServiceClass.__init__(self, id, serviceKeys, description)
        self._updateProperty('port', port)


    security.declareProtected('Manage DMD', 'manage_editServiceClass')
    def manage_editServiceClass(self, name="", monitor=False, serviceKeys="",
                               port=0, description="", sendString="",
                               expectRegex="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        self.sendString = sendString
        self.expectRegex = expectRegex
        return super(IpServiceClass,self).manage_editServiceClass(
                                name, monitor, serviceKeys,
                                port, description, REQUEST=REQUEST)
   


InitializeClass(IpServiceClass)
