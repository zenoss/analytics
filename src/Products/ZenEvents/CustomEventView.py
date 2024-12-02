##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.EventView")

from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_parent
from zope.interface import implements

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenEvents.EventFilter import EventFilter
from Products.ZenModel.EventView import IEventView

def manage_addCustomEventView(context, id, REQUEST=None):
    """Create an aciton rule"""
    ed = CustomEventView(id)
    context._setObject(id, ed)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main') 

addCustomEventView = DTMLFile('dtml/addCustomEventView',globals())

__pychecker__='no-argsused no-varargsused'

class CustomEventView(ZenModelRM, EventFilter):

    implements(IEventView)

    meta_type = "CustomEventView"

    type = "status"
    evtypes = ("status", "history")
    orderby = ""
    where = ""
    resultFields = ()

    _properties = ZenModelRM._properties + (
        {'id':'type', 'type':'selection',
            'select_variable':'evtypes', 'mode':'w'},
        {'id':'orderby', 'type':'string', 'mode':'w'},
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'resultFields', 'type':'lines', 'mode':'w'},
    )

    security = ClassSecurityInfo()

InitializeClass(CustomEventView)
