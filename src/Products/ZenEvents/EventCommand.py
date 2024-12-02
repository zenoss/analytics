##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.Commandable import Commandable
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenRelations.RelSchema import *
from AccessControl.class_init import InitializeClass
from EventFilter import EventFilter

class EventCommand(ZenModelRM, Commandable, EventFilter, ZenPackable):

    where = ''
    command = ''
    clearCommand = ''
    enabled = False
    delay = 0
    repeatTime = 0
    
    _properties = ZenModelRM._properties + (
        {'id':'command', 'type':'string', 'mode':'w'},
        {'id':'clearCommand', 'type':'string', 'mode':'w'},
        {'id':'where', 'type':'string', 'mode':'w'},
        {'id':'defaultTimeout', 'type':'int', 'mode':'w'},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'repeatTime', 'type':'int', 'mode':'w'},
    )
    
    _relations =  ZenPackable._relations + (
        ("eventManager", ToOne(ToManyCont, "Products.ZenEvents.EventManagerBase", "commands")),
    )

    security = ClassSecurityInfo()
        
    
InitializeClass(EventCommand)
