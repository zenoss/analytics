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
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import *
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from ZenPackable import ZenPackable


manage_addUserCommand = DTMLFile('dtml/addUserCommand',globals())


class UserCommand(ZenModelRM, ZenPackable):

    meta_type = 'UserCommand'

    security = ClassSecurityInfo()
  
    description = ""
    command = ''

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'command', 'type':'text', 'mode':'w'},
        )

    _relations =  ZenPackable._relations + (
        ("commandable", ToOne(
                ToManyCont, 'Products.ZenModel.Commandable', 'userCommands')),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'userCommandDetailNew',
        'actions'        :
        ( 
            {'id'            : 'overview',
             'name'          : 'User Command',
             'action'        : 'userCommandDetailNew',
             'permissions'   : ( Permissions.view, ),
            },
        )
    },
    )

    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object
        [('url','id'), ...]
        """
        crumbs = super(UserCommand, self).breadCrumbs(terminator)
        aqParent = self.getPrimaryParent()
        while aqParent.meta_type == 'ToManyContRelationship':
            aqParent = aqParent.getPrimaryParent()
        url = aqParent.absolute_url_path() + '/dataRootManage'
        return [(url, 'Commands')]
        
    def updateUserCommand(self, params):
        """
        params
        self.description
        self.command
        """
        self.command = params['command']
        self.description = params['description']
        

InitializeClass(UserCommand)
