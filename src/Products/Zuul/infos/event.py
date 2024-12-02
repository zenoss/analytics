##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009,2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import urllib
from zope.interface import implements
from zenoss.protocols.protobufs.zep_pb2 import EventSummary
from zenoss.protocols.protobufutil import ProtobufEnum
from zenoss.protocols.services.zep import EventStatus
from Products.ZenEvents.events2.proxy import EventProxy
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.Zuul.interfaces import IMarshallable
from lxml.html.clean import clean_html
from lxml.etree import ParserError


_status_name = ProtobufEnum(EventSummary, 'status').getPrettyName


def _mergeAuditLogToNotes(evtsumm):
    if 'audit_log' in evtsumm:
        mergedNotes = evtsumm.get('notes', [])
        for auditNote in evtsumm['audit_log']:
            mergedNotes.append({
                'created_time': auditNote['timestamp'],
                'user_uuid': auditNote.get('user_uuid', ''),
                'user_name': auditNote.get('user_name', ''),
                'message': 'state changed to {}'.format(
                    _status_name(auditNote['new_status'])
                ),
            })
        evtsumm['notes'] = mergedNotes
    return evtsumm


def _clean_html(html):
    """
    Cleans the document of each of the possible offending elements.
    Extends implementation from `lxml` which requires root element and
    adds it in case of its absence.
    """
    # Add root element to remove it after.
    wrapped_html = '<p>%s</p>' % (html, )
    cleaned_html = clean_html(wrapped_html)

    if cleaned_html.startswith('<p>') and cleaned_html.endswith('</p>'):
        return cleaned_html[3:-4]

    return cleaned_html


class EventCompatInfo(object):
    """
    Takes a zep event and maps it to the format that the UI expects
    """
    implements(IMarshallable)

    def __init__(self, dmd, event_summary):
        self._dmd = dmd
        self._event_summary = event_summary
        self._eventOccurrence = event_summary['occurrence'][0]
        self._eventActor = self._eventOccurrence['actor']
        self._eventDetails = self._findDetails(self._eventOccurrence)
        self._catalog = IModelCatalogTool(dmd)
        self._manager = IGUIDManager(dmd)

    @property
    def id(self):
        return self._event_summary['uuid']

    @property
    def evid(self):
        return self.id

    @property
    def dedupid(self):
        return self._eventOccurrence.get('fingerprint')

    @property
    def eventState(self):
        return EventStatus.getPrettyName(self._event_summary['status'])

    @property
    def severity(self):
        return self._eventOccurrence['severity']

    @property
    def component(self):
        return {
            'text': self._eventActor.get('element_sub_title'),
            'uid': self._getPathFromUuid(
                self._eventActor.get('element_sub_uuid')
            ),
            'url': self._uuidUrl(self._eventActor.get('element_sub_uuid')),
            'uuid': self._eventActor.get('element_sub_uuid')
        }

    @property
    def eventClass(self):
        eventClass = self._eventOccurrence['event_class']
        return {"text": eventClass, "uid": "/zport/dmd/Events%s" % eventClass}

    @property
    def summary(self):
        return self._eventOccurrence['summary']

    @property
    def firstTime(self):
        return self._event_summary['first_seen_time'] / 1000.0

    @property
    def lastTime(self):
        return self._event_summary['last_seen_time'] / 1000.0

    @property
    def count(self):
        return self._event_summary['count']

    @property
    def stateChange(self):
        return self._event_summary['status_change_time'] / 1000.0

    @property
    def eventClassKey(self):
        return self._eventOccurrence.get('event_class_key')

    @property
    def eventGroup(self):
        return self._eventOccurrence.get('event_group')

    @property
    def eventKey(self):
        return self._eventOccurrence.get('event_key')

    @property
    def agent(self):
        return self._eventOccurrence.get('agent')

    @property
    def monitor(self):
        return self._eventOccurrence.get('monitor')

    @property
    def ownerid(self):
        return self._event_summary.get('current_user_name')

    @property
    def facility(self):
        return self._eventOccurrence.get('syslog_facility')

    @property
    def priority(self):
        return self._eventOccurrence.get('syslog_priority')

    @property
    def eventClassMapping(self):
        return self._lookupEventClassMapping(
            self._eventOccurrence.get('event_class_mapping_uuid')
        )

    @property
    def clearid(self):
        return self._event_summary.get('cleared_by_event_uuid')

    @property
    def ntevid(self):
        return self._eventOccurrence.get('nt_event_code')

    @property
    def ipAddress(self):
        return self._eventDetails.get('zenoss.device.ip_address', '')

    @property
    def message(self):
        return self._eventOccurrence.get('message', '')

    @property
    def Location(self):
        return self._lookupDetailPath(
            '/zport/dmd/Locations',
            self._eventDetails.get(EventProxy.DEVICE_LOCATION_DETAIL_KEY)
        )

    @property
    def DeviceGroups(self):
        return self._lookupDetailPath(
            '/zport/dmd/Groups',
            self._eventDetails.get(EventProxy.DEVICE_GROUPS_DETAIL_KEY)
        )

    @property
    def Systems(self):
        return self._lookupDetailPath(
            '/zport/dmd/Systems',
            self._eventDetails.get(EventProxy.DEVICE_SYSTEMS_DETAIL_KEY)
        )

    @property
    def DeviceClass(self):
        return self._lookupDetailPath(
            '/zport/dmd/Devices',
            self._eventDetails.get(EventProxy.DEVICE_CLASS_DETAIL_KEY)
        )

    @property
    def device(self):
        device_url = self._get_device_url(self._eventDetails)
        if device_url is None:
            return dict(
                text=self._eventActor.get('element_title'),
                uid=self._getPathFromUuid(
                    self._eventActor.get('element_uuid')
                ),
                url=self._uuidUrl(self._eventActor.get('element_uuid')),
                uuid=self._eventActor.get('element_uuid')
            )
        else:
            return dict(text=self._eventActor.get('element_title'),
                        url=device_url)

    @property
    def prodState(self):
        prodState = self._singleDetail(
            self._eventDetails.get('zenoss.device.production_state')
        )
        if prodState is not None:
            return self._dmd.convertProdState(prodState)

    @property
    def DevicePriority(self):
        DevicePriority = self._singleDetail(
            self._eventDetails.get('zenoss.device.priority')
        )
        if DevicePriority is not None:
            return self._dmd.convertPriority(DevicePriority)

    @property
    def details(self):
        return self._eventDetails

    def __getattr__(self, name):
        if self._eventDetails.get(name):
            return self._eventDetails.get(name)
        raise AttributeError(name)

    def _uuidUrl(self, uuid):
        if uuid:
            return '/zport/dmd/goto?guid=%s' % uuid

    def _get_device_url(self, eventDetails):
        url_and_path = [
            self._singleDetail(eventDetails.get(k))
            for k in ('zenoss.device.url', 'zenoss.device.path')
        ]
        if len(url_and_path) != 2:
            return None
        url, path = url_and_path
        try:
            self._dmd.findChild(path)
        except Exception:
            return None
        return url

    def _singleDetail(self, value):
        """
        A convenience method for fetching a single detail from a property which
        correlates to a repeated field on the protobuf.
        """
        if isinstance(value, (tuple, list, set)) and value:
            return value[0]

    def _findDetails(self, event):
        """
        Event details are created as a dictionary like the following:
            detail = {
                'name': 'zenoss.foo.bar',
                'value': 'baz'
            }
        This method maps these detail items to a flat dictionary to facilitate
        looking up details by key easier.

        @rtype dict
        """
        details = {}
        if 'details' in event:
            for d in event['details']:
                details[d['name']] = d.get('value', ())
        return details

    def _lookupDetailPath(self, prefix, values):
        if not values:
            return ()
        paths = []
        for value in values:
            paths.append({'uid': prefix + value, 'name': value})
        return paths

    def _getPathFromUuid(self, uuid):
        if uuid:
            path = self._manager.getPath(uuid)
            if path:
                return urllib.unquote(path)

    def _lookupEventClassMapping(self, mappingUuid):
        if not mappingUuid:
            return ""

        return {
            'uuid': mappingUuid,
            'name': self._getNameFromUuid(mappingUuid)
        }

    def _getNameFromUuid(self, uuid):
        """
        Given a uuid this returns the objects name
        from the catalog, it does not wake the object up
        """
        if uuid:
            path = self._getPathFromUuid(uuid)
            if path:
                brain = self._catalog.getBrain(path, fields="name")
                if brain:
                    return brain.name


class EventCompatDetailInfo(EventCompatInfo):
    """
    Provides the extra fields needed for the details view of an event
    """
    implements(IMarshallable)

    def __init__(self, dmd, event_summary):
        super(EventCompatDetailInfo, self).__init__(dmd, event_summary)
        # add audit logs to the notes (for the log property)
        self._event_summary = _mergeAuditLogToNotes(self._event_summary)

        # event class mapping
        eventClassMapping = self._lookupEventClassMapping(
            self._eventOccurrence.get('event_class_mapping_uuid')
        )
        self._eventClassMappingName = self._eventClassMappingUrl = None
        if eventClassMapping:
            self._eventClassMappingName = eventClassMapping['name']
            self._eventClassMappingUrl = self._uuidUrl(
                eventClassMapping['uuid']
            )

    @property
    def component(self):
        return self._eventActor.get('element_sub_identifier')

    @property
    def component_title(self):
        return (
            self._getNameFromUuid(self._eventActor.get('element_sub_uuid')) or
            self._eventActor.get('element_sub_title')
        )

    @property
    def component_url(self):
        return self._uuidUrl(self._eventActor.get('element_sub_uuid'))

    @property
    def component_uuid(self):
        return self._eventActor.get('element_sub_uuid')

    @property
    def device_title(self):
        return self._eventActor.get('element_title')

    @property
    def device(self):
        return self._eventActor.get('element_identifier')

    @property
    def device_uuid(self):
        return self._eventActor.get('element_uuid')

    @property
    def device_url(self):
        d = super(EventCompatDetailInfo, self).device
        return d.get("url")

    @property
    def eventClassMapping(self):
        return self._eventClassMappingName

    @property
    def eventClassMapping_url(self):
        return self._eventClassMappingUrl

    @property
    def eventClass(self):
        return self._eventOccurrence['event_class']

    @property
    def eventClass_url(self):
        return "/zport/dmd/Events%s" % self.eventClass

    @property
    def details(self):
        d = []
        if 'details' in self._eventOccurrence:
            for detail in sorted(
                self._eventOccurrence['details'],
                key=lambda detail: detail['name'].lower()
            ):
                values = detail.get('value', ())
                if not isinstance(values, list):
                    values = list(values)
                for value in (v for v in values if v):
                    if not detail['name'].startswith('__meta__'):
                        try:
                            d.append(dict(
                                key=_clean_html(detail['name']),
                                value=_clean_html(value))
                            )
                        except ParserError:
                            d.append(dict(key=detail['name'], value=value))
        return d

    @property
    def log(self):
        logs = []
        if 'notes' in self._event_summary:
            self._event_summary['notes'].sort(
                key=lambda a: a['created_time'], reverse=True
            )
            for note in self._event_summary['notes']:
                logs.append((
                    note['user_name'],
                    note['created_time'],
                    note['message']
                ))
        return logs
