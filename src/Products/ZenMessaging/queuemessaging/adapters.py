##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zenoss.protocols.protobufs import zep_pb2 as eventConstants
from zenoss.protocols.protobufs import model_pb2 as modelConstants
from zope.interface import implementer

from Products.ZenEvents.events2.proxy import EventProxy
from Products.ZenMessaging.queuemessaging.interfaces import (
    IModelProtobufSerializer,
)
from Products.ZenUtils.guid.interfaces import (
    IGlobalIdentifier,
    IGloballyIdentifiable,
)

from .interfaces import IProtobufSerializer


class ObjectProtobuf(object):
    """
    Base class for common methods on the protobuf populators
    """

    def __init__(self, obj):
        self.obj = obj

    def _getGUID(self, obj):
        return IGlobalIdentifier(obj).create()

    def autoMapFields(self, proto):
        """
        This maps fields that have the same name from the
        adapted object to the protobuf
        """
        if IGloballyIdentifiable.providedBy(self.obj):
            proto.uuid = self._getGUID(self.obj)
        fields = proto.DESCRIPTOR.fields

        # attempt to match the fields that are named the same
        for field in fields:
            # already set
            if field.name == "uuid":
                continue
            value = getattr(self.obj, field.name, None)
            # we want 0's
            if value is None:
                continue
            try:
                if isinstance(value, basestring):
                    value = _safestr(value)
                setattr(proto, field.name, value)
            except (AttributeError, TypeError):
                # likely a composite field that we will have to set manually
                continue


@implementer(IModelProtobufSerializer)
class DeviceProtobuf(ObjectProtobuf):
    """
    Fills up the properties of a device protobuf.
    """


    @property
    def modelType(self):
        return "DEVICE"

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.title = _safestr(self.obj.titleOrId())
        return proto


@implementer(IModelProtobufSerializer)
class OrganizerProtobuf(ObjectProtobuf):
    """
    Fills up the properties of an organizer protobuf.
    """


    @property
    def modelType(self):
        return "ORGANIZER"

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.title = _safestr(self.obj.titleOrId())
        # get path minus first 3 '', 'zport', 'dmd'
        proto.path = "/".join(self.obj.getPrimaryPath()[3:])
        return proto


@implementer(IModelProtobufSerializer)
class DeviceComponentProtobuf(ObjectProtobuf):
    """
    Fills up the properties of a Device Component
    """


    @property
    def modelType(self):
        return "COMPONENT"

    def fill(self, proto):
        self.autoMapFields(proto)
        proto.title = _safestr(self.obj.name())
        # use device protobuf to fill out our device property
        device = self.obj.device()
        if device:
            populator = DeviceProtobuf(device)
            populator.fill(proto.device)
        return proto


def _safestr(s):
    """
    Defensive catchall to be sure that any string going into a protobuf can be
    decoded safely with UTF-8.  If any specialized encoding is desired, it
    is the responsibility of the caller/sender to take care of it.
    """
    if isinstance(s, str):
        try:
            s = unicode(s, "utf_8")
        except UnicodeDecodeError:
            # Could not force string to unicode so trying best effort
            # to treat as ASCII.
            s = str(s.decode("ascii", "replace"))
    elif not isinstance(s, basestring):
        s = str(s)
    return s


class EventProtobufMapper(object):
    """
    Base class for mapping a Event value (old-style) to a protobuf Event.
    """

    def mapEvent(self, proto, value):
        """
        Maps the event value to the protobuf.
        """
        pass


class EventProtobufStringMapper(EventProtobufMapper):
    """
    Performs a 1-1 mapping of an old event attribute to a corresponding
    field in the Event protobuf.
    """

    def __init__(self, fieldName):
        self._fieldName = fieldName

    def mapEvent(self, proto, value):
        setattr(proto, self._fieldName, _safestr(value))


class EventProtobufDeviceMapper(EventProtobufMapper):
    """
    Maps a 'device' to the corresponding location in the Event.EventActor.
    """

    def mapEvent(self, proto, value):
        proto.actor.element_type_id = modelConstants.DEVICE
        proto.actor.element_identifier = _safestr(value)


class EventProtobufDeviceGuidMapper(EventProtobufMapper):
    """
    Maps a 'device' to the corresponding location in the Event.EventActor.
    """

    def mapEvent(self, proto, value):
        proto.actor.element_type_id = modelConstants.DEVICE
        proto.actor.element_uuid = _safestr(value)


class EventProtobufComponentGuidMapper(EventProtobufMapper):
    """
    Maps a 'component' to the corresponding location in the Event.EventActor.
    """

    def mapEvent(self, proto, value):
        proto.actor.element_sub_type_id = modelConstants.COMPONENT
        proto.actor.element_sub_uuid = _safestr(value)


class EventProtobufComponentMapper(EventProtobufMapper):
    """
    Maps a 'component' to the corresponding location in the Event.EventActor.
    """

    def mapEvent(self, proto, value):
        if value:
            proto.actor.element_sub_type_id = modelConstants.COMPONENT
            proto.actor.element_sub_identifier = _safestr(value)


class EventProtobufSeverityMapper(EventProtobufMapper):
    """
    Maps an event severity to the EventSeverity enum value.
    """

    SEVERITIES = {
        "": eventConstants.SEVERITY_CLEAR,
        "0": eventConstants.SEVERITY_CLEAR,
        "1": eventConstants.SEVERITY_DEBUG,
        "2": eventConstants.SEVERITY_INFO,
        "3": eventConstants.SEVERITY_WARNING,
        "4": eventConstants.SEVERITY_ERROR,
        "5": eventConstants.SEVERITY_CRITICAL,
        "CLEAR": eventConstants.SEVERITY_CLEAR,
        "DEBUG": eventConstants.SEVERITY_DEBUG,
        "INFO": eventConstants.SEVERITY_INFO,
        "WARNING": eventConstants.SEVERITY_WARNING,
        "ERROR": eventConstants.SEVERITY_ERROR,
        "CRITICAL": eventConstants.SEVERITY_CRITICAL,
    }

    def mapEvent(self, proto, value):
        severity = str(value).upper()
        proto.severity = self.SEVERITIES.get(
            severity, eventConstants.SEVERITY_INFO
        )


class EventProtobufIntMapper(EventProtobufMapper):
    """
    Maps an event to an integer value in the protobuf.
    """

    def __init__(self, fieldName):
        self._fieldName = fieldName

    def mapEvent(self, proto, value):
        try:
            setattr(proto, self._fieldName, int(value))
        except ValueError:
            pass


class EventProtobufBoolMapper(EventProtobufMapper):
    """
    Maps an event to an integer value in the protobuf.
    """

    def __init__(self, fieldName):
        self._fieldName = fieldName

    def mapEvent(self, proto, value):
        try:
            setattr(proto, self._fieldName, bool(value))
        except ValueError:
            pass


class EventProtobufSyslogPriorityMapper(EventProtobufMapper):
    """
    Maps a syslog priority value to the corresponding SyslogPriority.*.
    """

    SYSLOG_PRIORITIES = {
        0: eventConstants.SYSLOG_PRIORITY_EMERG,
        1: eventConstants.SYSLOG_PRIORITY_ALERT,
        2: eventConstants.SYSLOG_PRIORITY_CRIT,
        3: eventConstants.SYSLOG_PRIORITY_ERR,
        4: eventConstants.SYSLOG_PRIORITY_WARNING,
        5: eventConstants.SYSLOG_PRIORITY_NOTICE,
        6: eventConstants.SYSLOG_PRIORITY_INFO,
        7: eventConstants.SYSLOG_PRIORITY_DEBUG,
    }

    def mapEvent(self, proto, value):
        try:
            proto.syslog_priority = self.SYSLOG_PRIORITIES[int(value)]
        except (KeyError, ValueError):
            pass


class EventProtobufDateMapper(EventProtobufMapper):
    """
    Maps a time.time() floating point value to the time in
    milliseconds as used by Event.
    """

    def __init__(self, fieldName):
        self._fieldName = fieldName

    def mapEvent(self, proto, value):
        setattr(proto, self._fieldName, int(value * 1000))


class EventProtobufDetailMapper(EventProtobufMapper):
    """
    Map's an event property to a new name in details.
    """

    def __init__(self, detailName):
        self._detailName = detailName

    def mapEvent(self, proto, value):
        proto.details.add(name=self._detailName, value=[value])


@implementer(IProtobufSerializer)
class EventProtobuf(ObjectProtobuf):
    """
    Fills up the properties of an event
    """


    # event property, protobuf property
    _FIELD_MAPPERS = {
        "dedupid": EventProtobufStringMapper("fingerprint"),
        "evid": EventProtobufStringMapper("uuid"),
        "device": EventProtobufDeviceMapper(),
        "device_guid": EventProtobufDeviceGuidMapper(),
        "component_guid": EventProtobufComponentGuidMapper(),
        "component": EventProtobufComponentMapper(),
        "eventClass": EventProtobufStringMapper("event_class"),
        "eventKey": EventProtobufStringMapper("event_key"),
        "summary": EventProtobufStringMapper("summary"),
        "message": EventProtobufStringMapper("message"),
        "severity": EventProtobufSeverityMapper(),
        "eventState": EventProtobufIntMapper("status"),
        "eventClassKey": EventProtobufStringMapper("event_class_key"),
        "eventGroup": EventProtobufStringMapper("event_group"),
        # stateChange -> Managed by ZEP
        "firstTime": EventProtobufDateMapper("first_seen_time"),
        "lastTime": EventProtobufDateMapper("created_time"),
        "count": EventProtobufIntMapper("count"),
        # prodState -> Added by zeneventd
        # suppid -> Added as a detail (deprecated)
        # manager -> Added as a detail (deprecated)
        "agent": EventProtobufStringMapper("agent"),
        # DeviceClass -> Added by zeneventd
        # Location -> Added by zeneventd
        # Systems -> Added by zeneventd
        # DeviceGroups -> Added by zeneventd
        "ipAddress": EventProtobufDetailMapper(
            EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY
        ),
        "facility": EventProtobufIntMapper("syslog_facility"),
        "priority": EventProtobufSyslogPriorityMapper(),
        "ntevid": EventProtobufIntMapper("nt_event_code"),
        # ownerid -> Managed by ZEP
        # clearid -> Managed by ZEP
        # DevicePriority -> Added by zeneventd
        # eventClassMapping -> Added by zeneventd
        "monitor": EventProtobufStringMapper("monitor"),
        "applyTransforms": EventProtobufBoolMapper("apply_transforms"),
    }

    # If these attributes are found on the Event they are not mapped and
    # are not placed into event details.
    _IGNORED_ATTRS = {
        "_action",
        "_clearClasses",
        "_fields",
        "stateChange",
        "prodState",
        "DeviceClass",
        "Location",
        "Systems",
        "DeviceGroups",
        "ownerid",
        "clearid",
        "DevicePriority",
        "eventClassMapping",
    }

    def __init__(self, obj):
        ObjectProtobuf.__init__(self, obj)

    def addDetail(self, proto, name, value):
        detail = proto.details.add()
        detail.name = name
        # Test whether 'value' is iterable.
        # Avoids strings because strings don't have an __iter__ method.
        if hasattr(value, "__iter__"):
            for v in value:
                detail.value.append(_safestr(v))
        else:
            detail.value.append(_safestr(value))

    def fill(self, proto):
        event = self.obj

        for key, value in event.__dict__.iteritems():
            if key in self._IGNORED_ATTRS or value is None:
                continue
            mapper = self._FIELD_MAPPERS.get(key)
            if mapper:
                mapper.mapEvent(proto, value)
            else:
                self.addDetail(proto, key, value)

        return proto
