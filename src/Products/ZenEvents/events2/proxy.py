##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from itertools import imap
from Products.ZenUtils.Time import LocalDateTimeFromMilli
from Products.ZenEvents.events2.fields import EventField, EventSummaryField, ZepRawEventField
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_SUPPRESSED,
    STATUS_CLOSED,
    STATUS_CLEARED,
    STATUS_DROPPED,
    STATUS_AGED,
    SEVERITY_CLEAR,
    EventTag,
    EventDetail
)
from zenoss.protocols.jsonformat import to_dict

import logging
log = logging.getLogger('zen.%s' % __name__)

class EventTagProxy(object):
    """
    A proxy for a tag UUID dictionary. Maps org.zenoss.protocols.zep.EventTag
    to a dictionary.
    """
    def __init__(self, eventProtobufWithTags):
        self._eventProtobuf = eventProtobufWithTags
        self._tags = {}
        self._load()

    def _load(self):
        for tag in self._eventProtobuf.tags:
            tag_uuids = self._tags.get(tag.type)
            if not tag_uuids:
                self._tags[tag.type] = tag_uuids = set()
            for tagUuid in tag.uuid:
                tag_uuids.add(tagUuid)

    def add(self, type, uuid):
        tag_uuids = self._tags.get(type)
        if not tag_uuids:
            self._tags[type] = tag_uuids = set()

        if not uuid in tag_uuids:
            tag_uuids.add(uuid)

            event_tag = None
            for tag in self._eventProtobuf.tags:
                if tag.type == type:
                    event_tag = tag
                    break
            else:
                event_tag = self._eventProtobuf.tags.add()
                event_tag.type = type

            event_tag.uuid.append(uuid)

    def addAll(self, type, uuids):
        for uuid in uuids:
            self.add(type, uuid)

    def getByType(self, type):
        return self._tags.get(type, ())

    def clearType(self, removetype):
        # accept a single type or a list of types - if a single value given, make it a 1-element list

        # if a generator was given, consume it into a temporary list
        if hasattr(removetype, 'next'):
            removetype = list(removetype)

        # make single value into a temporary list
        if not hasattr(removetype, '__iter__'):
            removetype = [removetype]

        # remove all entries from mapping
        for typ in removetype:
            if typ in self._tags:
                del self._tags[typ]

        # clear values from protobuf tags by assigning new list comprehension into
        # protobuf tags list in place (using [:] slice would be a lot easier, but not implemented)

        # This doesn't work - see http://code.google.com/p/protobuf/issues/detail?id=286
        #saveTags = [tag for tag in self._eventProtobuf.tags if tag.type not in removetype]
        saveTags = []
        for tag in self._eventProtobuf.tags:
            if tag.type not in removetype:
                cloned = EventTag()
                cloned.MergeFrom(tag)
                saveTags.append(cloned)

        del self._eventProtobuf.tags[:]
        self._eventProtobuf.tags.extend(saveTags)


class EventDetailProxy(object):
    """
    A proxy for a details dictionary. Maps org.zenoss.protocols.zep.EventDetail
    to a dictionary.
    """
    def __init__(self, eventProtobuf):
        self.__dict__['_eventProtobuf'] = eventProtobuf
        self.__dict__['_map'] = {}

        for detail in self._eventProtobuf.details:
            self._map[detail.name] = detail

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delitem__(self, key):
        if key in self._map:
            item = self._map.pop(key)
            # This doesn't work - see http://code.google.com/p/protobuf/issues/detail?id=286
            #savedetails = [det for det in self._eventProtobuf.details if det is not item]
            savedetails = []
            for det in self._eventProtobuf.details:
                if det.name != item.name:
                    cloned = EventDetail()
                    cloned.MergeFrom(det)
                    savedetails.append(cloned)
                    self._map[cloned.name] = cloned
            del self._eventProtobuf.details[:]
            self._eventProtobuf.details.extend(savedetails)

    def __getitem__(self, key):
        item = self._map[key]
        # Details are expected to be single values,
        # we'll just have to do our best to make it so
        if len(item.value) == 0:
            return None
        if len(item.value) == 1:
            return item.value[0]
        else:
            raise Exception('Detail %s has more than one value but the old event system expects only one: %s' % (item.name, item.value))

    def __setitem__(self, key, value):
        # Prep the field
        if value:
            if not key in self._map:
                item = self._eventProtobuf.details.add()
                item.name = key
                self._map[key] = item
            item = self._map[key]
            item.ClearField(EventField.Detail.VALUE)
            # Assume multivalue details
            if not isinstance(value, (set, list, tuple)):
                value = (value,)
            # Set each detail if it exists
            for val in imap(str, value):
                if val:
                    item.value.append(val)

    def __contains__(self, key):
        return key in self._map

    def __len__(self):
        return len(self._map)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def set(self, key, value):
        self[key] = value

    def getAll(self, key, default=None):
        """
        The normal __getitem__ and get() methods throw an exception for multi-valued details. This one specifically
        allows multi-valued details.
        """
        try:
            return self._map[key].value
        except KeyError:
            return default

class ProtobufWrapper(object):
    """
    Conveinence wrapper for protobufs to make sure fields
    are actually set.
    """
    def __init__(self, pb):
        self.__dict__['_pb'] = pb

    def get(self, key, default=None):
        if self._pb.HasField(key):
            return getattr(self._pb, key)
        else:
            return default

    def set(self, key, value):
        if isinstance(value, str):
            setattr(self.__dict__['_pb'], key, unicode(value, encoding='utf-8'))
        else:
            setattr(self.__dict__['_pb'], key, value)

    def __getattr__(self, name):
        return getattr(self._pb, name)

    def __setattr__(self, name, value):
        self.set(name, value)

    def __delattr__(self, name):
        self._pb.ClearField(name)

    def HasField(self, name):
        return self._pb.HasField(name)

class EventProxy(object):
    """
    Wraps an org.zenoss.protobufs.zep.Event
    and makes it look like an old style Event.
    """

    DEVICE_PRIORITY_DETAIL_KEY = "zenoss.device.priority"
    PRODUCTION_STATE_DETAIL_KEY = "zenoss.device.production_state"
    DEVICE_IP_ADDRESS_DETAIL_KEY = 'zenoss.device.ip_address'
    DEVICE_SYSTEMS_DETAIL_KEY = 'zenoss.device.systems'
    DEVICE_GROUPS_DETAIL_KEY = 'zenoss.device.groups'
    DEVICE_LOCATION_DETAIL_KEY = 'zenoss.device.location'
    DEVICE_CLASS_DETAIL_KEY = 'zenoss.device.device_class'
    COMPONENT_GROUP_DETAIL_KEY = 'zenoss.component.component_group'

    def __init__(self, eventProtobuf):
        self.__dict__['_event'] = ProtobufWrapper(eventProtobuf)
        self.__dict__['_clearClasses'] = set()
        self.__dict__['_readOnly'] = {}
        self.__dict__['details'] = EventDetailProxy(self._event)
        self.__dict__['_tags'] = EventTagProxy(self._event)

    def updateFromDict(self, data):
        for key, value in data.iteritems():
            setattr(self, key, value)

    @property
    def created(self):
        t = self._event.get(EventField.CREATED_TIME)
        if t:
            return t / 1000
    @property
    def agent(self):
        return self._event.get(EventField.AGENT)

    @agent.setter
    def agent(self, val):
        self._event.set(EventField.AGENT, val)

    @property
    def severity(self):
        return self._event.get(EventField.SEVERITY)

    @severity.setter
    def severity(self, val):
        self._event.set(EventField.SEVERITY, int(val))

    @property
    def device(self):
        return self._event.actor.element_identifier

    @device.setter
    def device(self, val):
        self._event.actor.element_identifier = val
        self._event.actor.element_type_id = DEVICE
        self._event.actor.ClearField(EventField.Actor.ELEMENT_UUID)

    @property
    def component(self):
        return self._event.actor.element_sub_identifier

    @component.setter
    def component(self, val):
        self._event.actor.element_sub_identifier = val
        self._event.actor.element_sub_type_id = COMPONENT
        self._event.actor.ClearField(EventField.Actor.ELEMENT_SUB_UUID)

    @property
    def eventClass(self):
        eventClassValue = self._event.get(EventField.EVENT_CLASS)
        if isinstance( eventClassValue, unicode ):
            eventClassValue = str( eventClassValue )
        return eventClassValue

    @eventClass.setter
    def eventClass(self, val):
        self._event.set(EventField.EVENT_CLASS, val)

    @property
    def prodState(self):
        state = self.details.get(EventProxy.PRODUCTION_STATE_DETAIL_KEY)
        if state:
            return int(state)

    @prodState.setter
    def prodState(self, val):
        self.details.set(EventProxy.PRODUCTION_STATE_DETAIL_KEY, int(val))

    @property
    def summary(self):
        return self._event.get(EventField.SUMMARY)

    @summary.setter
    def summary(self, val):
        self._event.set(EventField.SUMMARY, val)

    @property
    def message(self):
        return self._event.get(EventField.MESSAGE)

    @message.setter
    def message(self, val):
        self._event.set(EventField.MESSAGE, val)

    @property
    def facility(self):
        return self._event.get(EventField.SYSLOG_FACILITY)

    @facility.setter
    def facility(self, val):
        self._event.set(EventField.SYSLOG_FACILITY, val)

    @property
    def eventClassKey(self):
        return self._event.get(EventField.EVENT_CLASS_KEY)

    @eventClassKey.setter
    def eventClassKey(self, val):
        self._event.set(EventField.EVENT_CLASS_KEY, val)

    @property
    def dedupid(self):
        return self._event.get(EventField.FINGERPRINT)

    @dedupid.setter
    def dedupid(self, val):
        self._event.set(EventField.FINGERPRINT, val)

    @property
    def monitor(self):
        return self._event.get(EventField.MONITOR)

    @monitor.setter
    def monitor(self, val):
        self._event.set(EventField.MONITOR, val)

    @property
    def ntevid(self):
        return self._event.get(EventField.NT_EVENT_CODE)

    @ntevid.setter
    def ntevid(self, val):
        self._event.set(EventField.NT_EVENT_CODE, val)

    @property
    def DevicePriority(self):
        priority = self.details.get(EventProxy.DEVICE_PRIORITY_DETAIL_KEY)
        if priority:
            return int(priority)

    @DevicePriority.setter
    def DevicePriority(self, val):
        self.details.set(EventProxy.DEVICE_PRIORITY_DETAIL_KEY, int(val))

    @property
    def priority(self):
        return self._event.get(EventField.SYSLOG_PRIORITY)

    @priority.setter
    def priority(self, val):
        self._event.set(EventField.SYSLOG_PRIORITY, val)

    @property
    def evid(self):
        return self._event.get(EventField.UUID)

    @property
    def eventKey(self):
        return self._event.get(EventField.EVENT_KEY)

    @eventKey.setter
    def eventKey(self, val):
        self._event.set(EventField.EVENT_KEY, val)

    @property
    def eventGroup(self):
        return self._event.get(EventField.EVENT_GROUP)

    @eventGroup.setter
    def eventGroup(self, val):
        self._event.set(EventField.EVENT_GROUP, val)

    @property
    def ipAddress(self):
        return self.details.get(EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY)

    @ipAddress.setter
    def ipAddress(self, val):
        self.details.set(EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY, val)

    @property
    def DeviceClass(self):
        return self.details.get(EventProxy.DEVICE_CLASS_DETAIL_KEY)

    @DeviceClass.setter
    def DeviceClass(self, val):
        self.details.set(EventProxy.DEVICE_CLASS_DETAIL_KEY, val)

    @property
    def eventState(self):
        return self._event.get(EventSummaryField.STATUS, STATUS_NEW)

    @eventState.setter
    def eventState(self, val):
        self._event.set(EventSummaryField.STATUS, val)

    @property
    def tags(self):
        return self._tags

    @property
    def Location(self):
        return self.details.get(EventProxy.DEVICE_LOCATION_DETAIL_KEY)

    @property
    def Systems(self):
        values = self.details.getAll(EventProxy.DEVICE_SYSTEMS_DETAIL_KEY)
        if values:
            return '|' + '|'.join(values)

    @property
    def DeviceGroups(self):
        values = self.details.getAll(EventProxy.DEVICE_GROUPS_DETAIL_KEY)
        if values:
            return '|' + '|'.join(values)

    @property
    def flappingInterval(self):
        return self._event.get(EventField.FLAPPING_INTERVAL)

    @flappingInterval.setter
    def flappingInterval(self, val):
        self._event.set(EventField.FLAPPING_INTERVAL, val)

    @property
    def flappingThreshold(self):
        return self._event.get(EventField.FLAPPING_THRESHOLD)

    @flappingThreshold.setter
    def flappingThreshold(self, val):
        self._event.set(EventField.FLAPPING_THRESHOLD, val)

    @property
    def flappingSeverity(self):
        return self._event.get(EventField.FLAPPING_SEVERITY)

    @flappingSeverity.setter
    def flappingSeverity(self, val):
        self._event.set(EventField.FLAPPING_SEVERITY, val)

    def setReadOnly(self, name, value):
        """
        Adds a read only attribute for transforms to read.
        These properties are not sent with the event to the queue.
        """
        self._readOnly[name] = value

    def resetReadOnly(self, name):
        """
        Clears a read only attribute so it can be updated.
        """
        self._readOnly.pop(name, None)



    # Just put everything else in the details
    def __getattr__(self, name):
        if name in self._readOnly:
            return self._readOnly[name]

        try:
            return self.__dict__['details'][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if hasattr(self.__class__, name):
            object.__setattr__(self, name, value)
        else:
            self.__dict__['details'][name] = value

class EventSummaryProxy(EventProxy):
    """
    Wraps an org.zenoss.protobufs.zep.EventSummary

    and makes it look like an old style Event.
    """
    def __init__(self, eventSummaryProtobuf):
        self.__dict__['_eventSummary'] = ProtobufWrapper(eventSummaryProtobuf)
        if not self._eventSummary.occurrence:
            self._eventSummary.occurrence.add()

        event = self._eventSummary.occurrence[0]
        EventProxy.__init__(self, event)

    @property
    def evid(self):
        return self._eventSummary.get(EventSummaryField.UUID)

    @property
    def stateChange(self):
        t = self._eventSummary.get(EventSummaryField.STATUS_CHANGE_TIME)
        if t:
            return LocalDateTimeFromMilli(t)

    @property
    def clearid(self):
        return self._eventSummary.get(EventSummaryField.CLEARED_BY_EVENT_UUID)

    @clearid.setter
    def clearid(self, val):
        self._eventSummary.set(EventSummaryField.CLEARED_BY_EVENT_UUID, val)

    @property
    def firstTime(self):
        t = self._eventSummary.get(EventSummaryField.FIRST_SEEN_TIME)
        if t:
            return LocalDateTimeFromMilli(t)

    @property
    def lastTime(self):
        t = self._eventSummary.get(EventSummaryField.LAST_SEEN_TIME)
        if t:
            return LocalDateTimeFromMilli(t)

    @property
    def count(self):
        return self._eventSummary.get(EventSummaryField.COUNT, 0)

    @property
    def ownerid(self):
        return self._eventSummary.get(EventSummaryField.CURRENT_USER_NAME)

    @ownerid.setter
    def ownerid(self, val):
        self._eventSummary.set(EventSummaryField.CURRENT_USER_NAME, val)

    @property
    def eventState(self):
        return self._eventSummary.get(EventSummaryField.STATUS, STATUS_NEW)

    @eventState.setter
    def eventState(self, val):
        self._eventSummary.set(EventSummaryField.STATUS, val)

class ZepRawEventProxy(EventProxy):
    """
    Wraps an org.zenoss.protobufs.zep.ZepRawEvent and makes it look like
    an old style Event. It is the proper event proxy to use for transforms
    since transforms use _action and _clearClasses.
    """
    ACTION_HISTORY = 'history'
    ACTION_DROP = 'drop'
    ACTION_STATUS = 'status'
    ACTION_HEARTBEAT = 'heartbeat'
    ACTION_LOG = 'log'
    ACTION_ALERT_STATE = 'alert_state'
    ACTION_DETAIL = 'detail'

    ACTION_STATUS_MAP = {
        ACTION_HISTORY : STATUS_CLOSED,
        ACTION_STATUS : STATUS_NEW,
        ACTION_DROP : STATUS_DROPPED,
        None : STATUS_NEW,
    }

    STATUS_ACTION_MAP = {
        STATUS_NEW : ACTION_STATUS,
        STATUS_ACKNOWLEDGED : ACTION_STATUS,
        STATUS_SUPPRESSED : ACTION_STATUS,
        STATUS_CLOSED : ACTION_HISTORY,
        STATUS_CLEARED : ACTION_HISTORY,
        STATUS_DROPPED : ACTION_DROP,
        STATUS_AGED : ACTION_HISTORY,
        None : ACTION_STATUS,
    }

    def __init__(self, zepRawEvent):
        self.__dict__['_zepRawEvent'] = ProtobufWrapper(zepRawEvent)
        EventProxy.__init__(self, self._zepRawEvent.event)

        classes = []
        if self._zepRawEvent.clear_event_class:
            classes = list(self._zepRawEvent.clear_event_class)

        self.__dict__['_clearClassesSet'] = set(classes)
        self._refreshClearClasses()

    def __str__(self):
        return "{_zepRawEvent:%s}" % str(to_dict(self._zepRawEvent))

    def _refreshClearClasses(self):
        # Add this dynamically in case severity or event_class changes
        if self._event.severity == SEVERITY_CLEAR and self._event.get(EventField.EVENT_CLASS):
            self._clearClassesSet.add(self._event.event_class)

        del self._zepRawEvent.clear_event_class
        for eventClass in self._clearClassesSet:
            self._zepRawEvent.clear_event_class.append(eventClass)

    @property
    def _clearClasses(self):
        return list(self._clearClassesSet)

    @_clearClasses.setter
    def _clearClasses(self, val):
        self._clearClassesSet.clear()
        self._clearClassesSet.update(val)
        self._refreshClearClasses()

    @property
    def _action(self):
        return self.STATUS_ACTION_MAP.get(self.eventState, self.STATUS_ACTION_MAP[None])

    @_action.setter
    def _action(self, val):
        current_status = self.STATUS_ACTION_MAP.get(self.eventState)
        if current_status != val:
            self.eventState = self.ACTION_STATUS_MAP.get(val, self.ACTION_STATUS_MAP[None])

    @property
    def eventClassMapping(self):
        return self.details.get('eventClassMapping', '')

    @eventClassMapping.setter
    def eventClassMapping(self, val):
        # TODO: event_class_mapping_uuid needs to be set separately to avoid
        # duplicate lookups
        self.details['eventClassMapping'] = val


# add lists to introspect valid fields for types
for typ in (EventProxy, EventSummaryProxy):
    typ.FIELDS = [name for name in dir(typ) if isinstance(getattr(typ,name), property)]
