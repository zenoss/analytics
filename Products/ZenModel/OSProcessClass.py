##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Products.ZenModel.ZenossSecurity import *
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets import messaging
from ZenPackable import ZenPackable
from zope.component import adapter
from OFS.interfaces import IObjectWillBeRemovedEvent
from ZenModelRM import ZenModelRM

def manage_addOSProcessClass(context, id=None, REQUEST = None):
    """make a device class"""
    if id:
        context.manage_addOSProcessClass(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addOSProcessClass = DTMLFile('dtml/addOSProcessClass',globals())

class OSProcessClass(ZenModelRM, Commandable, ZenPackable):
    meta_type = "OSProcessClass"
    dmdRootName = "Processes"
    default_catalog = "processSearch"

    name = ""
    regex = ""
    excludeRegex = ".*(vim|tail|grep|tar|cat|bash).*"
    description = ""
    example = ""
    sequence = 0
    
    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'excludeRegex', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'example', 'type':'string', 'mode':'w'},
        ) 

    _relations = ZenPackable._relations + (
        ("instances", ToMany(ToOne, "Products.ZenModel.OSProcess", "osProcessClass")),
        ("osProcessOrganizer", 
            ToOne(ToManyCont,"Products.ZenModel.OSProcessOrganizer","osProcessClasses")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )


    factory_type_information = ( 
        { 
            'immediate_view' : 'osProcessClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'osProcessClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'osProcessClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'osProcessClassManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zProperties'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
   

    def __init__(self, id):
        self.title = id
        id = self.prepId(id)
        super(OSProcessClass, self).__init__(id)
        self.name = self.regex = id

    def getOSProcessClassName(self):
        """Return the full name of this process class.
        """
        return self.getPrimaryDmdId("Processes", "osProcessClasses")


    def match(self, procKey):
        """match procKey against our regex.
        """
        return re.search(self.regex, procKey)

        
    def count(self):
        """Return count of instances in this class.
        """
        return self.instances.countObjects()


    security.declareProtected('Manage DMD', 'manage_editOSProcessClass')
    def manage_editOSProcessClass(self,
                                  name="",
                                  zMonitor=True, 
                                  zAlertOnRestart=False,
                                  zFailSeverity=3,
                                  regex="",
                                  excludeRegex="",
                                  description="",
                                  REQUEST=None):
                                 
        """
        Edit a ProductClass from a web page.
        """
        from Products.ZenUtils.Utils import unused
        unused(zAlertOnRestart, zFailSeverity, zMonitor)
        # Left in name, added title for consistency
        self.title = name
        self.name = name
        id = self.prepId(name)
        redirect = self.rename(id)
        self.regex = regex
        self.excludeRegex = excludeRegex
        self.description = description
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            messaging.IMessageSender(self).sendToBrowser(
                'Product Class Saved',
                SaveMessage()
            )
            return self.callZenScreen(REQUEST, redirect)
   

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return self.instances()
        
    
    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/osProcessClassManage'


    def getPrimaryParentOrgName(self):
        ''' Return the organizer name for the primary parent
        '''
        return self.getPrimaryParent().getOrganizerName()


InitializeClass(OSProcessClass)

@adapter(OSProcessClass, IObjectWillBeRemovedEvent)
def onProcessClassRemoved(ob, event):
    # if _operation is set to 1 it means we are moving it, not deleting it
    if getattr(ob, '_operation', None) != 1:
        for i in ob.instances():
            i.manage_deleteComponent()
        
