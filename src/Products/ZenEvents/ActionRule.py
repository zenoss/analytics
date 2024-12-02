##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.ActionRule")

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenEvents.EventFilter import EventFilter

class ActionRule(ZenModelRM, EventFilter):
    """
    Rule applied to events that then executes an action on matching events.
    """
    
    meta_type = "ActionRule"

    where = "severity >= 4 and eventState = 0 and prodState = 1000"
    delay = 0
    repeatTime = 0
    action = "email"
    format = "[zenoss] %(device)s %(summary)s"
    body =  "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severityString)s\n" \
            "Time: %(firstTime)s\n" \
            "Message:\n%(message)s\n" \
            "<a href=\"%(eventUrl)s\">Event Detail</a>\n" \
            "<a href=\"%(ackUrl)s\">Acknowledge</a>\n" \
            "<a href=\"%(deleteUrl)s\">Delete</a>\n" \
            "<a href=\"%(eventsUrl)s\">Device Events</a>\n"
    sendClear = True
    clearFormat = "[zenoss] CLEAR: %(device)s %(clearOrEventSummary)s"
    clearBody =  \
            "Event: '%(summary)s'\n" \
            "Cleared by: '%(clearSummary)s'\n" \
            "At: %(clearFirstTime)s\n" \
            "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severityString)s\n" \
            "Message:\n%(message)s\n" \
            "<a href=\"%(undeleteUrl)s\">Undelete</a>\n"
    enabled = False
    actionTypes = ("page", "email") 
    targetAddr = ""
    plainText = False

    _properties = ZenModelRM._properties + (
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'format', 'type':'text', 'mode':'w'},
        {'id':'body', 'type':'text', 'mode':'w'},
        {'id':'sendClear', 'type':'boolean', 'mode':'w'},
        {'id':'clearFormat', 'type':'text', 'mode':'w'},
        {'id':'clearBody', 'type':'text', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'action', 'type':'selection', 'mode':'w',
            'select_variable': 'actionTypes',},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'targetAddr', 'type':'string', 'mode':'w'},
        {'id':'repeatTime', 'type':'int', 'mode':'w'},
        {'id':'plainText', 'type':'boolean', 'mode':'w'},
    )

    _relations = (
        ("windows", ToManyCont(ToOne,"Products.ZenEvents.ActionRuleWindow","actionRule")),
        )

    security = ClassSecurityInfo()

    def getUser(self):
        """Return the user this action is for.
        """
        return self.getPrimaryParent()

    def getUserid(self):
        """Return the userid this action is for.
        """
        return self.getUser().getId()

InitializeClass(ActionRule)
