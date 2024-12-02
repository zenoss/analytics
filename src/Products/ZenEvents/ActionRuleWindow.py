##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.ActionRuleWindow")

from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow
from Products.ZenRelations.RelSchema import *

class ActionRuleWindow(MaintenanceWindow):

    backCrumb = 'editActionRuleSchedule'      # FIXME

    actionRule = None
    
    _relations = (
        ("actionRule", ToOne(ToManyCont,"Products.ZenEvents.ActionRule","windows")),
        )
        
    security = ClassSecurityInfo()
