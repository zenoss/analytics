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

from decorator import decorator
from copy import deepcopy
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.class_init import InitializeClass
from zope.interface import Interface, implements
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul import getFacade
from Products.ZenWidgets import messaging
from zenoss.protocols.services import ServiceResponseError
from zenoss.protocols.services.zep import ZepConnectionError
from urllib3.exceptions import ProtocolError
from zenoss.protocols.protobufs.zep_pb2 import (STATUS_NEW, STATUS_ACKNOWLEDGED, SEVERITY_CRITICAL,
                                                SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG)

class IEventView(Interface):
    """
    Marker interface for objects which have event views.
    """

def zepConnectionError(retval=None):
    def outer(func):
        def inner(func, self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ZepConnectionError as e:
                msg = 'Connection refused. Check zeneventserver status on <a href="/zport/dmd/daemons">Services</a>'
                messaging.IMessageSender(self).sendToBrowser("ZEP connection error",
                                                        msg,
                                                        priority=messaging.CRITICAL,
                                                        sticky=True)
                log.warn("Could not connect to ZEP")
            except ProtocolError as e:
                msg = '"No status line received before ZEP closed the http connection". Check zeneventserver status on <a href="/zport/dmd/daemons">Services</a>'
                messaging.IMessageSender(self).sendToBrowser("ZEP closed the connection before sending a status line",
                                                        msg,
                                                        priority=messaging.CRITICAL,
                                                        sticky=True)
                log.warn("ZEP closed the connection before sending a status line.")
            return deepcopy(retval)    # don't return the mutable retval
        return decorator(inner, func)  # for URL's through Zope we must use the same arguments as the original function
    return outer

class EventView(object):
    """
    This class provides convenience methods for retrieving events to any subclass. Note that
    this class is currently transitioning between the old event system and ZEP. Most of the methods
    are marked as deprecated except those that go through ZEP.

    """
    implements(IEventView)

    security = ClassSecurityInfo()

    def getEventManager(self, table='status'):
        """Return the current event manager for this object.
        """
        if table=='history':
            return self.ZenEventHistory
        return self.ZenEventManager

    def getStatusString(self, statclass, **kwargs):
        """Return the status number for this device of class statClass.
        """
        # used to avoid pychecker complaint about wrong # of args to getStatus
        f = self.getStatus
        return self.convertStatus(f(statclass, **kwargs))

    @zepConnectionError(())
    def getEventSummary(self, severity=1, state=1, prodState=None):
        """Return an event summary list for this managed entity.
        """
        zep = getFacade('zep', self.dmd)
        sevsum = []
        try:
            # Event class rainbows show all events through DEBUG severity
            sevs = (SEVERITY_CRITICAL,SEVERITY_ERROR,SEVERITY_WARNING,SEVERITY_INFO,SEVERITY_DEBUG)
            severities = zep.getEventSeveritiesByUuid(self.getUUID(), severities=sevs)
            getCssClass = self.getEventManager().getEventCssClass
            for sev in sorted(severities.keys(), reverse=True):
                if sev < severity:
                    continue
                counts = severities[sev]
                count = counts.get('count', 0)
                acked = counts.get('acknowledged_count', 0)
                sevsum.append([getCssClass(sev), acked, count])
        except TypeError as e:
            log.warn("Attempted to query events for %r which does not have a uuid", self)
        return sevsum

    def getStatusImgSrc(self, status):
        ''' Return the image source for a status number
        '''
        return self.getEventManager().getStatusImgSrc(status)

    def getStatusCssClass(self, status):
        """Return the css class for a status number.
        """
        return self.getEventManager().getStatusCssClass(status)

    def _getCurrentUserName(self):
        return getSecurityManager().getUser().getId()

    def _redirectToEventConsole(self, msg, REQUEST=None):
        messaging.IMessageSender(self).sendToBrowser("Events",
                                                     msg,
                                                     priority=messaging.INFO)
        if REQUEST:
            dest = '/zport/dmd/Events/evconsole'
            REQUEST['RESPONSE'].redirect(dest)

    security.declareProtected('Manage Events','manage_ackEvents')
    @zepConnectionError()
    def manage_ackEvents(self, evids=(), REQUEST=None):
        """Set event state from this managed entity.
        """
        if not evids:
            self._redirectToEventConsole("No events to acknowledge", REQUEST)
            return

        zep = getFacade('zep', self.dmd)
        if isinstance(evids, basestring):
            evids = [evids]

        try:
            evids_filter = zep.createEventFilter(uuid=evids)
            zep.acknowledgeEventSummaries(eventFilter=evids_filter)
            self._redirectToEventConsole("Acknowledged events: %s" % ", ".join(evids), REQUEST)
        except ServiceResponseError as e:
            self._redirectToEventConsole("Error acknowledging events: %s" % str(e), REQUEST)

    security.declareProtected('Manage Events','manage_deleteEvents')
    @zepConnectionError()
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        """Delete events from this managed entity.
        """
        if not evids:
            self._redirectToEventConsole("No events to close", REQUEST)
            return

        zep = getFacade('zep', self.dmd)
        if isinstance(evids, basestring):
            evids = [evids]
        try:
            evids_filter = zep.createEventFilter(uuid=evids)
            zep.closeEventSummaries(eventFilter=evids_filter)
            self._redirectToEventConsole("Closed events: %s" % ", ".join(evids), REQUEST)
        except ServiceResponseError as e:
            self._redirectToEventConsole("Error Closing events: %s" % str(e), REQUEST)

    security.declareProtected('Manage Events','manage_undeleteEvents')
    @zepConnectionError()
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        """Delete events from this managed entity.
        """
        if not evids:
            self._redirectToEventConsole("No events to reopen", REQUEST)
            return

        zep = getFacade('zep', self.dmd)
        if isinstance(evids, basestring):
            evids = [evids]
        try:
            evids_filter = zep.createEventFilter(uuid=evids)
            zep.reopenEventSummaries(eventFilter=evids_filter)
            self._redirectToEventConsole("Reopened events: %s" % ", ".join(evids), REQUEST)
        except ServiceResponseError as e:
            self._redirectToEventConsole("Error Reopening events: %s" % str(e), REQUEST)

    @zepConnectionError(0)
    def getStatus(self, statusclass=None, **kwargs):
        """
        Return the status number for this device of class statClass.
        """
        zep = getFacade('zep', self.dmd)
        try:
            event_filter = zep.createEventFilter(tags=[self.getUUID()],
                                                 severity=[SEVERITY_WARNING,SEVERITY_ERROR,SEVERITY_CRITICAL],
                                                 status=[STATUS_NEW,STATUS_ACKNOWLEDGED],
                                                 event_class=filter(None, [statusclass]))
        except TypeError as e:
            log.warn("Attempted to query events for %r which does not have a uuid", self)
            return 0
        result = zep.getEventSummaries(0, filter=event_filter, limit=0)
        return int(result['total'])

    @zepConnectionError({})
    def getEventSeveritiesCount(self):
        """
        Uses the zep facade to return a list of
        event summaries for this entity
        """
        zep = getFacade('zep', self.dmd)
        try:
            # Event class rainbows show all events through DEBUG severity
            sevs = (SEVERITY_CRITICAL,SEVERITY_ERROR,SEVERITY_WARNING,SEVERITY_INFO,SEVERITY_DEBUG)
            severities = zep.getEventSeveritiesByUuid(self.getUUID(), severities=sevs)
        except TypeError as e:
            log.warn("Attempted to query events for %r which does not have a uuid", self)
            return {}
        results = dict((zep.getSeverityName(sev).lower(), counts) for (sev, counts) in severities.iteritems())
        return results

    @zepConnectionError(0)
    def getWorstEventSeverity(self):
        """
        Uses Zep to return the worst severity for this object
        """
        zep = getFacade('zep', self.dmd)
        try:
            result =  zep.getWorstSeverityByUuid(self.getUUID())
        except TypeError as e:
            log.warn("Attempted to query events for %r which does not have a uuid", self)
            result = 0
        return result

    def getUUID(self):
        return IGlobalIdentifier(self).getGUID()
    
InitializeClass(EventView)
