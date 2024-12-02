##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import time
import logging
from itertools import takewhile, chain

from AccessControl.class_init import InitializeClass
from collections import defaultdict
from Products.ZenUtils import Map
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenEvents.ZenEventClasses import Status_Ping, Status_Snmp
from Products.ZenEvents.ZenEventClasses import Status_OSProcess
from Products.Zuul import getFacade
from Products.AdvancedQuery import And, Eq, Generic, Or
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from zenoss.protocols.protobufs.zep_pb2 import (SEVERITY_CRITICAL, SEVERITY_ERROR,
                                                SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG, SEVERITY_CLEAR)
from zenoss.protocols.protobufs.zep_pb2 import (STATUS_NEW, STATUS_ACKNOWLEDGED,
                                                STATUS_SUPPRESSED, STATUS_CLOSED,
                                                STATUS_CLEARED, STATUS_DROPPED,
                                                STATUS_AGED)

log = logging.getLogger("zen.Availability")

ALL_EVENT_STATUSES = set([STATUS_NEW, STATUS_ACKNOWLEDGED,
                        STATUS_SUPPRESSED, STATUS_CLOSED,
                        STATUS_CLEARED, STATUS_DROPPED,
                        STATUS_AGED])
CLOSED_EVENT_STATUSES = set([STATUS_CLOSED, STATUS_CLEARED,
                             STATUS_DROPPED, STATUS_AGED])
OPEN_EVENT_STATUSES = ALL_EVENT_STATUSES - CLOSED_EVENT_STATUSES

def _severityGreaterThanOrEqual(sev):
    """function to return a list of severities >= the given severity;
       defines severity priority using arbitrary order, instead of
       assuming numeric ordering"""
    severities_in_order = (SEVERITY_CRITICAL,
                           SEVERITY_ERROR,
                           SEVERITY_WARNING,
                           SEVERITY_INFO,
                           SEVERITY_DEBUG,
                           SEVERITY_CLEAR)
    return list(takewhile(lambda x : x != sev, severities_in_order)) + [sev,]

def _lookupUuid(catalog, cls, identifier):
    """function to retrieve uuid given an object's catalog, type, and identifier"""
    result = catalog.getOrganizer(identifier)
    return IGlobalIdentifier(result).getGUID()

from AccessControl import ClassSecurityInfo

CACHE_TIME = 60.

_cache = Map.Locked(Map.Timed({}, CACHE_TIME))

def _round(value):
    if value is None: return None
    return (value // CACHE_TIME) * CACHE_TIME

def _findComponent(device, name):
    for c in device.getMonitoredComponents():
        if c.name() == name:
            return c
    return None

class Availability(object):
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    @staticmethod
    def getDefaultAvailabilityStart(dmd):
        return time.time() - dmd.ZenEventManager.defaultAvailabilityDays*24*60*60

    @staticmethod
    def getDefaultAvailabilityEnd():
        return time.time()

    # Simple record for holding availability information
    def __init__(self, device, component, downtime, total, systems='', link='', title=''):
        self.device = device
        self.systems = systems
        self.component = component
        self.link = link
        self.title = title

        # Guard against endDate being equal to or less than startDate.
        if total <= 0:
            self.availability = 0 if downtime else 1
        else:
            self.availability = max(0, 1 - (float(downtime) / total))

    def floatStr(self):
        return '%2.3f%%' % (self.availability * 100)

    def __str__(self):
        return self.floatStr()

    def __repr__(self):
        return '[%s %s %s]' % (self.device, self.component, self.floatStr())

    def __float__(self):
        return float(self.availability)

    def __int__(self):
        return int(self.availability * 100)

    def __eq__(self, other):
        if not isinstance(other, Availability):
            return False
        this = (self.availability, self.device, self.component())
        that = (other.availability, other.device, other.component())
        return this == that

    def __lt__(self, other):
        if not isinstance(other, Availability):
            return NotImplemented
        this = (self.availability, self.device, self.component())
        that = (other.availability, other.device, other.component())
        return this < that

    def getDevice(self, dmd):
        return dmd.Devices.findDevice(self.device)

    def getComponent(self, dmd):
        if self.device and self.component:
            device = self.getDevice(dmd)
            if device:
                return _findComponent(device, self.component)
        return None

    def getDeviceLink(self, dmd=None):
        if self.link:
            return self.link
        if dmd:
            device = self.getDevice(dmd)
        if device:
            return device.getDeviceLink()
        return None

InitializeClass(Availability)

class Report(object):
    "Determine availability by counting the amount of time down"

    def __init__(self,
                 startDate = None,
                 endDate = None,
                 eventClass=Status_Ping,
                 severity=5,
                 device=None,
                 component='',
                 prodState=1000,
                 manager=None,
                 agent=None,
                 DeviceClass=None,
                 Location=None,
                 System=None,
                 DeviceGroup=None,
                 DevicePriority=None,
                 monitor=None):
        self.startDate = _round(startDate)
        self.endDate = _round(endDate)
        self.eventClass = eventClass
        self.severity = int(severity) if severity is not None else None
        self.device = device
        self.component = component
        self.prodState = int(prodState) if prodState is not None else None
        self.manager = manager
        self.agent = agent
        self.DeviceClass = DeviceClass
        self.Location = Location if Location != '/' else None
        self.System = System if System != '/' else None
        self.DeviceGroup = DeviceGroup if DeviceGroup != '/' else None
        self.DevicePriority = int(DevicePriority) if DevicePriority is not None else None
        self.monitor = monitor

    def tuple(self):
        return (
            self.startDate, self.endDate, self.eventClass, self.severity,
            self.device, self.component, self.prodState, self.manager,
            self.agent, self.DeviceClass, self.Location, self.System,
            self.DeviceGroup, self.DevicePriority, self.monitor)

    def __hash__(self):
        return hash(self.tuple())

    def __eq__(self, other):
        if not isinstance(other, Report):
            return False
        if self is other:
            return True
        return self.tuple() == other.tuple()

    def __lt__(self, other):
        if not isinstance(other, Report):
            return NotImplemented
        if self is other:
            return False
        return self.tuple() < other.tuple()

    def __le__(self, other):
        if not isinstance(other, Report):
            return NotImplemented
        if self is other:
            return True
        return self.tuple() <= other.tuple()

    def run(self, dmd):
        """Run the report, returning an Availability object for each device"""
        # Note: we don't handle overlapping "down" events, so down
        # time could get get double-counted.
        __pychecker__='no-local'
        now = time.time()
        zep = getFacade("zep", dmd)

        path = '/zport/dmd/'

        pathFilterList = [Generic('path',{'query':path})]
        
        if self.DeviceClass:
            pathFilterList.append(Generic('path',{'query': ''.join([path,'Devices',self.DeviceClass])}))
        if self.Location:
            pathFilterList.append(Generic('path',{'query': ''.join([path,'Locations',self.Location])}))
        if self.System:
            pathFilterList.append(Generic('path',{'query':''.join([path,'Systems',self.System])}))
        if self.DeviceGroup:
            pathFilterList.append(Generic('path',{'query':''.join([path,'Groups',self.DeviceGroup])}))
        if self.device:
            pathFilterList.append(Or(Eq('name', self.device), Eq('id', self.device)))

        results = IModelCatalogTool(dmd.Devices).search(types='Products.ZenModel.Device.Device',
                query=And(*pathFilterList), fields=["uid", "uuid"])

        if not results.total:
            return []

        deviceList = {}
        tag_uuids = []
        accumulator = defaultdict(int)
        for brain in results:
            try:
                obj = brain.getObject()
                deviceList[obj.id] = obj
                tag_uuids.append(brain.uuid)
                accumulator[obj.id] = 0
            except Exception:
                log.warn("Unable to unbrain at path %s", brain.getPath())

        endDate = self.endDate or Availability.getDefaultAvailabilityEnd()
        endDate = min(endDate, now)
        startDate = self.startDate
        if not startDate:
            startDate = Availability.getDefaultAvailabilityStart(dmd)

        # convert start and end date to integer milliseconds for defining filters
        startDate = int(startDate*1000)
        endDate = int(endDate*1000)
        total_report_window = endDate - startDate

        create_filter_args = {
            'operator' : zep.AND,
            'severity' : _severityGreaterThanOrEqual(self.severity),
            'event_class' : self.eventClass +
                            ('/' if not self.eventClass.endswith('/') else '')
        }

        if self.agent:
            create_filter_args['agent'] = self.agent
        if self.monitor is not None:
            create_filter_args['monitor'] = self.monitor

        # add filters on details
        filter_details = {}
        if self.DevicePriority is not None:
            filter_details['zenoss.device.priority'] = "%d:" % self.DevicePriority
        if self.prodState:
            filter_details['zenoss.device.production_state'] = "%d:" % self.prodState
        if filter_details:
            create_filter_args['details'] = filter_details

        create_filter_args['tags'] = tag_uuids

        # query zep for matching event summaries
        # 1. get all open events that:
        #    - first_seen < endDate
        #    (only need to check active events)
        # 2. get all closed events that:
        #    - first_seen < endDate
        #    - status_change > startDate
        #    (must get both active and archived events)

        # 1. get open events
        create_filter_args['first_seen'] = (0,endDate)
        create_filter_args['status'] = OPEN_EVENT_STATUSES
        event_filter = zep.createEventFilter(**create_filter_args)
        open_events = zep.getEventSummariesGenerator(event_filter)

        # 2. get closed events
        create_filter_args['status_change'] = (startDate+1,)
        create_filter_args['status'] = CLOSED_EVENT_STATUSES
        event_filter = zep.createEventFilter(**create_filter_args)
        closed_events = zep.getEventSummariesGenerator(event_filter)
        # must also get events from archive
        closed_events_from_archive = zep.getEventSummariesGenerator(event_filter, archive=True)

        def eventDowntime(evt):
            first = evt['first_seen_time']
            # if event is still open, downtime persists til end of report window
            if evt['status'] not in CLOSED_EVENT_STATUSES:
                last = endDate
            else:
                last = evt['status_change_time']

            # discard any events that have no elapsed time
            if first == last:
                return 0

            # clip first and last within report time window
            first = max(first, startDate)
            last = min(last, endDate)

            return (last - first)

        def eventElementIdentifier(evt):
            return evt['occurrence'][0]['actor'].get('element_identifier')

        for evt in open_events:
            dt = eventDowntime(evt)
            if dt == 0:
                continue
            accumulator[eventElementIdentifier(evt)] += dt

        summary_closed_event_uuids = {}
        for evt in closed_events:
            summary_closed_event_uuids[evt['uuid']] = True
            dt = eventDowntime(evt)
            if dt == 0:
                continue
            accumulator[eventElementIdentifier(evt)] += dt

        for evt in closed_events_from_archive:
            if evt['uuid'] in summary_closed_event_uuids:
                continue
            dt = eventDowntime(evt)
            if dt == 0:
                continue
            accumulator[eventElementIdentifier(evt)] += dt

        availabilityReport = []
        for deviceId, downtime in sorted(accumulator.items()):
            device = deviceList.get(deviceId, None)
            if device:
                sysname = device.getSystemNamesString()
                link = device.getDeviceLink()
                title = device.titleOrId()
                availabilityReport.append(Availability(deviceId, '', downtime, total_report_window, sysname, link, title))
                device._p_invalidate()
        return availabilityReport

def query(dmd, *args, **kwargs):
    r = Report(*args, **kwargs)
    try:
        return _cache[r.tuple()]
    except KeyError:
        result = r.run(dmd)
        _cache[r.tuple()] = result
        return result


if __name__ == '__main__':
    import pprint
    r = Report(time.time() - 60*60*24*30)
    start = time.time() - 60*60*24*30
    # r.component = 'snmp'
    r.component = None
    r.eventClass = Status_Snmp
    r.severity = 3
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    z = ZCmdBase()
    pprint.pprint(r.run(z.dmd))
    a = query(z.dmd, start, device='gate.zenoss.loc', eventClass=Status_Ping)
    assert 0 <= float(a[0]) <= 1.
    b = query(z.dmd, start, device='gate.zenoss.loc', eventClass=Status_Ping)
    assert a == b
    assert id(a) == id(b)
    pprint.pprint(r.run(z.dmd))
    r.component = 'httpd'
    r.eventClass = Status_OSProcess
    r.severity = 4
    pprint.pprint(r.run(z.dmd))
    r.device = 'gate.zenoss.loc'
    r.component = ''
    r.eventClass = Status_Ping
    r.severity = 4
    pprint.pprint(r.run(z.dmd))
