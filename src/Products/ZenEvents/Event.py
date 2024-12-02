##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time

from Products.ZenEvents.ZenEventClasses import *
from Products.ZenEvents.Exceptions import *

from twisted.spread import pb

def buildEventFromDict(evdict):
    """Build an event object from a dictionary.
    """
    evclass = evdict.get("eventClass", Unknown)
    if evclass == Heartbeat:
        for field in ("device", "component", "timeout"):
            if field not in evdict:
                raise ZenEventError("Required event field %s not found: %s" % (field, evdict))
        evt = EventHeartbeat(evdict['device'], evdict['component'], 
                             evdict['timeout'])
    else:
        evt = Event(**evdict)
    return evt



class Event(pb.Copyable, pb.RemoteCopy):
    """
    Event that lives independant of zope context.  As interface that allows
    it to be persisted to/from the event backend.
    dedupid,
    evid,
    device,
    ipAddress,
    component,
    eventClass,
    eventGroup,
    eventKey,
    facility,
    severity,
    priority,
    summary,
    message,
    stateChange,
    firstTime,
    lastTime,
    count,
    prodState,
    DevicePriority,
    manager,
    agent,
    DeviceClass,
    Location,
    Systems,
    DeviceGroups,
    """
    
    def __init__(self, rcvtime=None, **kwargs):
        # not sure we need sub second time stamps
        # if we do uncomment and change event backend to use
        # double presicion values for these two fields.
        if not rcvtime:
            self.firstTime = self.lastTime = time.time()
        else:
            self.firstTime = self.lastTime = rcvtime
        self._clearClasses = []
        self._action = "status"
        self._fields = kwargs.get('fields',[])
        self.eventKey = ''
        self.component = ''
        if kwargs: self.updateFromDict(kwargs)

    
    def getEventFields(self):
        """return an array of event fields tuples (field,value)"""
        return [(x, getattr(self, x)) for x in self._fields]


    # DEPRECATE THIS METHOD - not used anywhere
    #def getEventData(self):
    #    """return an list of event data"""
    #    return [ getattr(self, x) for x in self._fields]


    def updateFromFields(self, fields, data):
        """
        Update event from list of fields and list of data values.  
        They must have the same length.  To be used when pulling data 
        from the backend db.
        """
        self._fields = fields
        data = [d if d is not None else '' for d in data]
        for field,val in zip(fields, data):
            setattr(self, field, val)


    def updateFromDict(self, data):
        """Update event from dict.  Keys that don't match attributes are
        put into the detail list of the event.
        """
        for key, value in data.items():
            setattr(self, key, value)

    def clone(self):
        ret = self.__class__(**self.__dict__)
        # make copies of lists, instead of just duplicating refs to them
        ret._fields = self._fields[:]
        ret._clearClasses = self._clearClasses[:]
        return ret

    def clearClasses(self):
        """Return a list of classes that this event clears.
        if we have specified clearClasses always return them
        if we ave a 0 severity return ourself as well.
        """
        clearcls = self._clearClasses
        evclass = getattr(self, "eventClass", None)
        sev = getattr(self, 'severity', None)
        if evclass and sev == 0: 
            clearcls.append(self.eventClass)

        # collapse out duplicates
        clearcls = list(set(clearcls))
        return clearcls


    # DEPRECATE THIS METHOD - not used anywhere
    #def getDataList(self, fields):
    #    """return a list of data elements that map to the fields parameter.
    #    """
    #    return map(lambda x: getattr(self, x), fields)


    def getDedupFields(self, default):
        """Return list of dedupid fields.
        """
        return default
pb.setUnjellyableForClass(Event, Event)



class EventHeartbeat(Event):

    eventClass = Heartbeat

    def __init__(self, device, component, timeout=120):
        self._fields = ("device", "component", "timeout")
        Event.__init__(self, device=device, component=component,timeout=timeout)
pb.setUnjellyableForClass(EventHeartbeat, EventHeartbeat)
