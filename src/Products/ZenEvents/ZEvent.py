##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Event import Event

class ZEvent(Event):
    """
    Event that lives in the zope context has zope security mechanisms and
    url back to event manager
    """
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
 
    def __init__(self, manager, fields, data, eventPermission=True):
        Event.__init__(self)
        self.updateFromFields(fields, data)
        self._zem = manager.getId()
        self._baseurl = manager.absolute_url_path()
        self.eventPermission = eventPermission

    def getEventDetailHref(self):
        """build an href to call the detail of this event"""
        return "%s/viewEventFields?evid=%s" % (self._baseurl, self.evid)

    def getCssClass(self):
        """return the css class name to be used for this event.
        """
        __pychecker__='no-constCond'
        value = self.severity < 0 and "unknown" or self.severity
        acked = self.eventState > 0 and "acked" or "noack"
        return "zenevents_%s_%s %s" % (value, acked, acked)

    def zem(self):
        """return the id of our manager.
        """
        return self._zem

InitializeClass(ZEvent)
