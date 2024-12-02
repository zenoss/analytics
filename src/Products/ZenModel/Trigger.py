##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.triggers")

from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo
from AdministrativeRoleable import AdministrativeRoleable
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from zope.interface import implements
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable


class InvalidTriggerActionType(Exception): pass

class DuplicateTriggerName(Exception): pass

def manage_addTriggerManager(context, REQUEST=None):
    """Create the trigger manager."""
    tm = TriggerManager(TriggerManager.root)
    context._setObject(TriggerManager.root, tm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

class TriggerManager(ZenModelRM):
    """Manage triggers."""

    _id = "TriggerManager"
    root = 'Triggers'
    meta_type = _id

    sub_meta_types = ("Trigger",)

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Management of triggers""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addTriggerManager',
            'immediate_view' : 'editSettings',
            'actions'        : (
                {
                    'id'            : 'settings',
                    'name'          : 'Settings',
                    'action'        : '../editSettings',
                    'permissions'   : ( ZEN_MANAGE_DMD, )
                })
         },
    )

addTrigger = DTMLFile('dtml/addTrigger',globals())


def manage_addTrigger(context, id, title = None, REQUEST = None):
    """Create a trigger"""
    ns = Trigger(id, title)
    context._setObject(id, ns)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

class Trigger(ZenModelRM, AdministrativeRoleable):
    """
    A stub object that is used for managing permissions.
    """
    implements(IGloballyIdentifiable)
    security = ClassSecurityInfo()

    _id = "Trigger"
    meta_type = _id

    _properties = ZenModelRM._properties

    _relations = (
        ("adminRoles",
        ToManyCont(
            ToOne,
            "Products.ZenModel.AdministrativeRole",
            "managedObject"
        )),
    )

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Stub object representing a trigger.""",
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addTrigger',
            'immediate_view' : 'editTrigger',
            'actions'        :(
                {
                    'id'            : 'edit',
                    'name'          : 'Edit',
                    'action'        : 'editTrigger',
                    'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                }
            )
         },
    )

    # a property storing user permission mappings
    users = []

    def __init__(self, id, title=None, buildRelations=True):
        self.globalRead = False
        self.globalWrite = False
        self.globalManage = False

        self.userRead = False
        self.userWrite = False
        self.userManage = False

        super(ZenModelRM, self).__init__(id, title=title, buildRelations=buildRelations)

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editTrigger')
    def manage_editTrigger(self, REQUEST=None):
        """Update trigger properties"""
        return self.zmanage_editProperties(REQUEST)

InitializeClass(TriggerManager)
InitializeClass(Trigger)
