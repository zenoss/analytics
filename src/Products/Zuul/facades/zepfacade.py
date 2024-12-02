##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import re
from AccessControl import getSecurityManager
from zope.interface import implements
from Products.ZenModel.Device import Device
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IZepFacade
from Products.ZenEvents.ZenEventClasses import Unknown

from zenoss.protocols.interfaces import IQueueSchema
from zenoss.protocols.services.zep import ZepStatsClient, ZepServiceClient, \
                                        EventSeverity, ZepConfigClient, \
                                        ZepHeartbeatClient
from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import (
    EventSort, EventFilter, EventSummaryUpdateRequest, ZepConfig, EventNote,
    EventSummaryUpdate, EventDetailSet, ZepStatistics
)
from zenoss.protocols.protobufutil import listify
from Products.ZenUtils import safeTuple
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO, \
     SEVERITY_DEBUG, SEVERITY_CLEAR, STATUS_NEW, STATUS_ACKNOWLEDGED, STATUS_SUPPRESSED, OR, AND
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.ZenEvents.ZenEventClasses import Status_Ping
from zope.component import getUtility
from uuid import uuid4
from Products.ZenEvents.Event import Event as ZenEvent
from Products.ZenEvents.events2.proxy import EventProxy
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from functools import partial
from time import time

log = logging.getLogger(__name__)


class InvalidQueryParameterException(Exception):
    """
    Raised when a query is attempted with invalid search criteria.
    """

class NoFiltersException(Exception):
    """
    Raised when an operation that requires filters is called without them.
    closeEventSummaries, reopenEventSummaries or acknowledgeEventSummaries
    raise this exception.
    """

class ZepFacade(ZuulFacade):
    implements(IZepFacade)

    AND = AND
    OR = OR

    DEFAULT_SORT_MAP = {
        'eventstate':    { 'field': EventSort.STATUS },
        'eventstatetext':{ 'field': EventSort.STATUS },
        'severity':      { 'field': EventSort.SEVERITY },
        'firsttime':     { 'field': EventSort.FIRST_SEEN },
        'lasttime':      { 'field': EventSort.LAST_SEEN },
        'eventclass':    { 'field': EventSort.EVENT_CLASS },
        'device':        { 'field': EventSort.ELEMENT_TITLE },
        'component':     { 'field': EventSort.ELEMENT_SUB_TITLE },
        'count':         { 'field': EventSort.COUNT },
        'summary':       { 'field': EventSort.EVENT_SUMMARY },
        'ownerid':       { 'field': EventSort.CURRENT_USER_NAME },
        'agent':         { 'field': EventSort.AGENT },
        'monitor':       { 'field': EventSort.MONITOR },
        'eventkey':      { 'field': EventSort.EVENT_KEY },
        'evid':          { 'field': EventSort.UUID },
        'statechange':   { 'field': EventSort.STATUS_CHANGE },
        'dedupid':       { 'field': EventSort.FINGERPRINT },
        'eventclasskey': { 'field': EventSort.EVENT_CLASS_KEY },
        'eventgroup':    { 'field': EventSort.EVENT_GROUP },
    }

    SORT_DIRECTIONAL_MAP = {
        'asc' : EventSort.ASCENDING,
        'desc' : EventSort.DESCENDING,
    }

    ZENOSS_DETAIL_OLD_TO_NEW_MAPPING = {
        'prodState': EventProxy.PRODUCTION_STATE_DETAIL_KEY,
        'DevicePriority': EventProxy.DEVICE_PRIORITY_DETAIL_KEY,
        'ipAddress': EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY,
        'Location': EventProxy.DEVICE_LOCATION_DETAIL_KEY,
        'DeviceGroups': EventProxy.DEVICE_GROUPS_DETAIL_KEY,
        'Systems': EventProxy.DEVICE_SYSTEMS_DETAIL_KEY,
        'DeviceClass': EventProxy.DEVICE_CLASS_DETAIL_KEY,
    }
    ZENOSS_DETAIL_NEW_TO_OLD_MAPPING = dict((new, old) for old, new in ZENOSS_DETAIL_OLD_TO_NEW_MAPPING.iteritems())

    JAVA_MIN_INTEGER = -2147483648
    # Values that zep uses to index details with no value
    ZENOSS_NULL_NUMERIC_DETAIL_INDEX_VALUE = JAVA_MIN_INTEGER
    ZENOSS_NULL_TEXT_DETAIL_INDEX_VALUE = '\x07'

    SEVERITIES_BATCH_SIZE = 400

    COUNT_REGEX = re.compile(r'^(?P<from>\d+)?:?(?P<to>\d+)?$')

    def __init__(self, context):
        super(ZepFacade, self).__init__(context)
        config = getGlobalConfiguration()
        zep_url = config.get('zep-uri', 'http://localhost:8084')
        schema = getUtility(IQueueSchema)
        self.client = ZepServiceClient(zep_url, schema)
        self.configClient = ZepConfigClient(zep_url, schema)
        self.heartbeatClient = ZepHeartbeatClient(zep_url, schema)
        self._guidManager = IGUIDManager(context.dmd)
        self.statsClient = ZepStatsClient(zep_url, schema)

    def _create_identifier_filter(self, value):
        if not isinstance(value, (tuple, list, set)):
            value = (value,)
        return map(lambda s:str(s).strip(), value)

    def _createFullTextSearch(self, parameter):
        if not hasattr(parameter, '__iter__'):
            parameter = (parameter,)
        return map(lambda s:str(s).strip(), parameter)

    def createEventFilter(self,
        severity=(),
        status=(),
        event_class=(),
        first_seen=None,
        last_seen=None,
        status_change=None,
        update_time=None,
        count_range=None,
        element_identifier=(),
        element_title=(),
        element_sub_identifier=(),
        element_sub_title=(),
        uuid=(),
        event_summary=None,
        tags=(),
        fingerprint=(),
        agent=(),
        monitor=(),
        event_key=(),
        current_user_name=(),
        subfilter=(),
        operator=None,
        details=None,
        event_class_key=(),
        event_group=(),
        message=()):
        """
        Creates a filter based on passed arguments.
        Caller is responsible for handling the include-zero-items case.
        For example, passing an empty uuid tuple won't filter by uuid so includes everything.
        """

        filter = {}

        if uuid:
            filter['uuid'] = uuid

        if event_summary:
            filter['event_summary'] = self._createFullTextSearch(event_summary)

        if event_class:
            filter['event_class'] = event_class

        if status:
            filter['status'] = status

        if severity:
            filter['severity'] = severity

        if first_seen:
            filter['first_seen'] = self._timeRange(first_seen)

        if last_seen:
            filter['last_seen'] = self._timeRange(last_seen)

        if status_change:
            filter['status_change'] = self._timeRange(status_change)

        if update_time:
            filter['update_time'] = self._timeRange(update_time)

        # These tags come from params, which means for some reason someone is filtering manually on a tag.
        if tags:
            filter['tag_filter'] = {'tag_uuids': tags}

        if count_range:
            if not isinstance(count_range, (tuple, list)):
                try:
                    count = int(count_range)
                    count_range = (count, count)
                except ValueError:
                    match = ZepFacade.COUNT_REGEX.match(count_range)
                    if not match:
                        raise ValueError('Invalid range: %s' % (count_range))
                    count_range = (match.group('from'), match.group('to'))

            filter['count_range'] = {}
            count_from, count_to = count_range
            if count_from is not None:
                filter['count_range']['from'] = int(count_from)
            if count_to is not None:
                filter['count_range']['to'] = int(count_to)

        if element_identifier:
            filter['element_identifier'] = self._create_identifier_filter(element_identifier)

        if element_title:
            filter['element_title'] = self._create_identifier_filter(element_title)

        if element_sub_identifier:
            filter['element_sub_identifier'] = self._create_identifier_filter(element_sub_identifier)

        if element_sub_title:
            filter['element_sub_title'] = self._create_identifier_filter(element_sub_title)

        if fingerprint:
            filter['fingerprint'] = fingerprint

        if agent:
            filter['agent'] = agent

        if monitor:
            filter['monitor'] = monitor

        if event_key:
            filter['event_key'] = event_key

        if current_user_name:
            filter['current_user_name'] = current_user_name

        if subfilter:
            filter['subfilter'] = subfilter

        if details:
            filter['details'] = self._createEventDetailFilter(details)

        if event_class_key:
            filter['event_class_key'] = event_class_key

        if event_group:
            filter['event_group'] = event_group

        if message:
            filter['message'] = self._createFullTextSearch(message)

        # Everything's repeated on the protobuf, so listify
        result = dict((k, listify(v)) for k,v in filter.iteritems())

        if operator:
            result['operator'] = operator

        return result


    def _createEventDetailFilter(self, details):
        """
        @param details: All details present in this filter request.

        Example: {
            'zenoss.device.production_state' = 4,
            'zenoss.device.priority' : 2
        }

        @type details: dict
        """

        detailFilterItems = []

        for key, val in details.iteritems():
            detailFilterItems.append({
               'key': key,
                'value': val,
            })

        log.debug('Final detail filter: %r', detailFilterItems)
        return detailFilterItems

    def _timeRange(self, timeRange):
        d = {
            'start_time' : timeRange[0],
        }

        if len(timeRange) == 2:
            d['end_time'] = timeRange[1]

        return d

    def _getEventSort(self, sortParam):
        eventSort = {}
        if isinstance(sortParam, (list, tuple)):
            field, direction = sortParam
            eventSort['direction'] = self.SORT_DIRECTIONAL_MAP[direction.lower()]
        else:
            field = sortParam
        eventSort.update(getDetailsInfo().getSortMap()[field.lower()])
        return from_dict(EventSort, eventSort)

    def _getUserUuid(self, userName):
        # We have to call _getOb instead of getUserSettings here because the
        # latter will create a new user settings object even if the user is
        # not known.
        try:
            user = self._dmd.ZenUsers._getOb(userName)
            return IGlobalIdentifier(user).getGUID()
        except AttributeError:
            raise Exception('Could not find user "%s"' % userName)

    def _findUserInfo(self):
        userName = getSecurityManager().getUser().getId()
        return self._getUserUuid(userName), userName

    def addNote(self, uuid, message, userName, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)

        self.client.addNote(uuid, message, userUuid, userName)

    def addNoteBulkAsync(self, uuids, message, userName, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)

        self.client.addNoteBulkAsync(uuids, message, userUuid, userName)

    def postNote(self, uuid, note):
        self.client.postNote(uuid, from_dict(EventNote, note))


    def _getEventSummaries(self, source, offset, limit=1000):
        response, content = source(offset=offset, limit=limit)
        return {
            'total' : content.total,
            'limit' : content.limit,
            'next_offset' : content.next_offset if content.HasField('next_offset') else None,
            'events' : (to_dict(event) for event in content.events),
        }

    def getEventSummariesFromArchive(self, offset, limit=1000, sort=None, filter=None, exclusion_filter=None):
        return self.getEventSummaries(offset, limit, sort, filter,
                                      client_fn=self.client.getEventSummariesFromArchive, exclusion_filter=exclusion_filter)

    def getEventSummaries(self, offset, limit=1000, sort=None, filter=None, exclusion_filter=None, client_fn=None,
                          use_permissions=False):
        if client_fn is None:
            client_fn = self.client.getEventSummaries
        if filter is not None and isinstance(filter,dict):
            filter = from_dict(EventFilter, filter)
        if exclusion_filter is not None and isinstance(exclusion_filter, dict):
            exclusion_filter['operator'] = 1 # Set operator to OR
            exclusion_filter = from_dict(EventFilter, exclusion_filter)
        if sort is not None:
            sort = tuple(self._getEventSort(s) for s in safeTuple(sort))

        result = None

        if use_permissions:
            user = getSecurityManager().getUser()
            userSettings = self._dmd.ZenUsers._getOb(user.getId())
            hasGlobalRoles = not userSettings.hasNoGlobalRoles()
            if not hasGlobalRoles:
                # get guids for the objects user has permission to access
                # and add to filter
                guids = userSettings.getAllAdminGuids(returnChildrenForRootObj=True)
                if guids:
                    if filter is None:
                        filter = EventFilter()
                    tf = filter.tag_filter.add()
                    tf.tag_uuids.extend(guids)
                else:
                    # no permission to see events, return 0
                    result =  {
                        'total' : 0,
                        'events' : [],
                    }

        if not result:
            result = self._getEventSummaries(source=partial(client_fn,
                                                   filter=filter,
                                                   exclusion_filter=exclusion_filter,
                                                   sort=sort
                                                   ),
                                           offset=offset, limit=limit
                                           )
        return result

    def getEventSummariesGenerator(self, filter=None, exclude=None, sort=None, archive=False, timeout=None):
        if isinstance(exclude, dict):
            exclude = from_dict(EventFilter, exclude)
        if isinstance(filter, dict):
            filter = from_dict(EventFilter, filter)
        if sort is not None:
            sort = tuple(self._getEventSort(s) for s in safeTuple(sort))
        searchid = self.client.createSavedSearch(event_filter=filter, exclusion_filter=exclude, sort=sort,
                                                 archive=archive, timeout=timeout)
        log.debug("created saved search %s", searchid)
        eventSearchFn = partial(self.client.savedSearch, searchid, archive=archive)
        offset = 0
        limit = 1000
        try:
            while offset is not None:
                result = self._getEventSummaries(eventSearchFn, offset, limit)
                for evt in result['events']:
                    yield evt
                offset = result['next_offset']
        finally:
            try:
                log.debug("closing saved search %s", searchid)
                self.client.deleteSavedSearch(searchid, archive=archive)
            except Exception as e:
                log.debug("error closing saved search %s (%s) - %s", searchid, type(e), e)

    def getEventSummary(self, uuid):
        response, content = self.client.getEventSummary(uuid)
        return to_dict(content)

    def nextEventSummaryUpdate(self, next_request):
        status, response = self.client.nextEventSummaryUpdate(from_dict(EventSummaryUpdateRequest, next_request))
        return status, to_dict(response)

    def _processArgs(self, eventFilter, exclusionFilter, userName):
        if eventFilter:
            eventFilter = from_dict(EventFilter, eventFilter)
        if exclusionFilter:
            exclusionFilter = from_dict(EventFilter, exclusionFilter)

        if not userName:
            userUuid, userName = self._findUserInfo()
        else:
            userUuid = self._getUserUuid(userName)

        if eventFilter is None and exclusionFilter is None:
            raise NoFiltersException("Cannot modify event summaries without at least one filter specified.")

        return {'eventFilter': eventFilter, 'exclusionFilter': exclusionFilter,
                'userName': userName, 'userUuid': userUuid}

    def closeEventSummaries(self, eventFilter=None, exclusionFilter=None, limit=None, userName=None, timeout=None):
        arguments = self._processArgs(eventFilter, exclusionFilter, userName)
        eventFilter = arguments.get('eventFilter')
        exclusionFilter = arguments.get('exclusionFilter')
        userName = arguments.get('userName')
        userUuid = arguments.get('userUuid')
        status, response = self.client.closeEventSummaries(
            userUuid, userName, eventFilter, exclusionFilter, limit, timeout=timeout)
        return status, to_dict(response)

    def acknowledgeEventSummaries(self, eventFilter=None, exclusionFilter=None, limit=None, userName=None,
                                  timeout=None):
        arguments = self._processArgs(eventFilter, exclusionFilter, userName)
        eventFilter = arguments.get('eventFilter')
        exclusionFilter = arguments.get('exclusionFilter')
        userName = arguments.get('userName')
        userUuid = arguments.get('userUuid')
        status, response = self.client.acknowledgeEventSummaries(userUuid, userName, eventFilter, exclusionFilter,
                                                                 limit, timeout=timeout)
        return status, to_dict(response)

    def reopenEventSummaries(self, eventFilter=None, exclusionFilter=None, limit=None, userName=None, timeout=None):
        arguments = self._processArgs(eventFilter, exclusionFilter, userName)
        eventFilter = arguments.get('eventFilter')
        exclusionFilter = arguments.get('exclusionFilter')
        userName = arguments.get('userName')
        userUuid = arguments.get('userUuid')
        status, response = self.client.reopenEventSummaries(
            userUuid, userName, eventFilter, exclusionFilter, limit, timeout=timeout)
        return status, to_dict(response)

    def updateEventSummaries(self, update, eventFilter=None, exclusionFilter=None, limit=None, timeout=None):
        update_pb = from_dict(EventSummaryUpdate, update)
        event_filter_pb = None if (eventFilter is None) else from_dict(EventFilter, eventFilter)
        exclusion_filter_pb = None if (exclusionFilter is None) else from_dict(EventFilter, exclusionFilter)
        status, response = self.client.updateEventSummaries(update_pb, event_filter_pb, exclusion_filter_pb,
                                                            limit=limit, timeout=timeout)
        return status, to_dict(response)

    def getConfig(self):
        # the config client doesn't return a ZepConfig. It merges the ZepConfig
        # with some other properties to create a config structure.
        config = self.configClient.getConfig()
        return config

    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        zepConfigProtobuf = from_dict(ZepConfig, values)
        self.configClient.setConfigValues(zepConfigProtobuf)

    def setConfigValue(self, name, value):
        self.configClient.setConfigValue(name, value)

    def removeConfigValue(self, name):
        self.configClient.removeConfigValue(name)

    def _getTopLevelOrganizerUuids(self, tagUuid):
        """
        Returns a list of child UUIDs if the specified tagUuid is a top-level
        organizer. Otherwise returns None. This is needed because several
        operations in ZEP are performed on UUIDs tagged in the events, however
        the top-level organizers are not tagged on events as an optimization.

        @type  tagUuid: string
        @param tagUuid: UUID of potential top-level organizer
        """
        obj = self._guidManager.getObject(tagUuid)
        uuids = None
        if obj and obj.getDmdKey() == '/':
            uuids = [IGlobalIdentifier(n).getGUID() for n in obj.children()]
        return uuids

    def getEventSeveritiesByUuid(self, tagUuid, severities=(), status=()):
        """ returns a dict of severities for the element tagUuid """
        uuids = [ tagUuid ]
        return self.getEventSeveritiesByUuids(uuids , severities=severities, status=status)[tagUuid]


    def getEventSeveritiesByUuids(self, tagUuids, severities=(), status=()):
        """ returns a dict whose keys are each uuid in tagUuids and values the dict of severities per uuid """
        uuids = []
        requested_uuids = {}
        for uuid in tagUuids:
            children_uuids = self._getTopLevelOrganizerUuids(uuid)
            if children_uuids:
                requested_uuids[uuid] = children_uuids
                uuids.extend(children_uuids)
            else:
                requested_uuids[uuid] = [ uuid ]
                uuids.append(uuid)

        uuids = list(set(uuids))
        severities = self.getEventSeverities(uuids, severities=severities, status=status)

        severities_to_return = {}

        for requested_uuid in requested_uuids.keys():
            children_uuids = requested_uuids[requested_uuid]
            sevmap = {}
            for uuid in children_uuids:
                sevs = severities[uuid]
                for sev, counts in sevs.iteritems():
                    counts_dict = sevmap.get(sev)
                    if counts_dict:
                        # Condense counts of child organizers into a flattened out count
                        counts_dict['count'] += counts['count']
                        counts_dict['acknowledged_count'] += counts['acknowledged_count']
                    else:
                        sevmap[sev] = counts
            severities_to_return[requested_uuid] = sevmap
        return severities_to_return

    def _createSeveritiesDict(self, eventTagSeverities):
        severities = {}

        for tag in eventTagSeverities:
            severities[tag.tag_uuid] = {}
            for sev in tag.severities:
                severities[tag.tag_uuid][sev.severity] = dict(count=sev.count,
                                                              acknowledged_count=sev.acknowledged_count)
            for sev in EventSeverity.numbers:
                if not sev in severities[tag.tag_uuid]:
                    severities[tag.tag_uuid][sev] = dict(count=0, acknowledged_count=0)

        return severities

    def getEventSeverities(self, tagUuids, severities=(), status=(), eventClass=()):
        """
        Get a dictionary of the event severity counts for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @param severities: A sequence of severities to include. Default is CRITICAL/ERROR/WARNING.
        @type  severities: Sequence of severities.
        @param status: A sequence of event statuses to include. Default is NEW/ACKNOWLEDGED.
        @type  status: Sequence of event severities.
        @rtype: dict
        @return: A dictionary of UUID -> { C{EventSeverity} -> { count, acknowledged_count } }
        """
        objects_severities = {}
        tagUuids = list(tagUuids)
        tagUuids.sort()
        number_of_uuids = len(tagUuids)
        batch_size = ZepFacade.SEVERITIES_BATCH_SIZE

        number_of_batches = number_of_uuids / batch_size
        if (number_of_uuids % batch_size) > 0:
            number_of_batches = number_of_batches + 1

        if number_of_batches > 1:
            log.info("Retrieving severities for %s uuids.", number_of_uuids)

        for batch in range(0, number_of_batches):
            start = batch*batch_size
            end = (start + batch_size)
            if end > number_of_uuids:
                end = number_of_uuids
            uuids = tagUuids[start:end]

            eventTagSeverities = self._getEventTagSeverities(severity=severities, status=status, tags=uuids, eventClass=eventClass)
            objects_severities.update(self._createSeveritiesDict(eventTagSeverities))

        return objects_severities

    def getWorstSeverityByUuid(self, tagUuid, default=SEVERITY_CLEAR, ignore=()):
        return self.getWorstSeverity([tagUuid], default=default, ignore=ignore)[tagUuid]

    def getWorstSeverity(self, tagUuids, default=SEVERITY_CLEAR, ignore=()):
        """
        Get a dictionary of the worst event severity for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @param default: The default severity to use if there are no results or if a severity is ignored
        @type default: An C{EventSeverity} enum value
        @param ignore: Severities to not include as worst, use the default instead.
        @type ignore: A list of C{EventSeverity} enum values
        @rtype: dict
        @return: A dictionary of UUID -> C{EventSeverity}
        """
        if not tagUuids:
            return {}

        # Prepopulate the list with defaults
        severities = dict.fromkeys(tagUuids, default)
        eventTagSeverities = self._getEventTagSeverities(tags=tagUuids)
        for tag in eventTagSeverities:
            for sev in tag.severities:
                if sev.severity not in ignore:
                    severities[tag.tag_uuid] = max(sev.severity, severities.get(tag.tag_uuid, 0))
        return severities

    def getSeverityName(self, severity):
        return EventSeverity.getPrettyName(severity)

    def createEventMapping(self, evdata, eventClassId):
        """
        Associates event(s) with an event class.
        """
        evmap = None
        evclass = self._dmd.Events.getOrganizer(eventClassId)
        numCreated = 0
        numNotUnknown = 0
        numNoKey = 0

        for data in evdata:
            evclasskey = data.get('eventClassKey')
            if data.get('eventClass'):
                curevclass = data.get('eventClass')['text']
            else:
                curevclass = Unknown
            example = data.get('message')
            if curevclass != Unknown:
                numNotUnknown += 1
                continue
            if not evclasskey:
                numNoKey += 1
                continue
            evmap = evclass.createInstance(evclasskey)
            evmap.eventClassKey = evclasskey
            evmap.example = example
            evmap.index_object()
            numCreated += 1
        # message
        msg = ''
        if numNotUnknown:
            msg += ((msg and ' ') +
                    '%s event%s %s not of the class Unknown.' % (
                        numNotUnknown,
                        (numNotUnknown != 1 and 's') or '',
                        (numNotUnknown != 1 and 'are') or 'is'))
        if numNoKey:
            msg += ((msg and ' ') +
                    '%s event%s %s not have an event class key.' % (
                        numNoKey,
                        (numNoKey != 1 and 's') or '',
                        (numNoKey != 1 and 'do') or 'does'))
        msg += (msg and ' ') + 'Created %s event mapping%s.' % (
                        numCreated,
                        (numCreated != 1 and 's') or '')
        # redirect
        url = None
        if len(evdata) == 1 and evmap:
            url = evmap.getPrimaryId()
        elif evclass and evmap:
            url = evclass.getPrimaryId()
        return msg, url

    def _getEventTagSeverities(self, eventClass=(), severity=(), status=(), tags=(), deviceOnly=False):
        if not severity:
            severity = (SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING)
        if not status:
            status = (STATUS_NEW, STATUS_ACKNOWLEDGED)
        if deviceOnly:
            eventFilter = self.createEventFilter(
                severity=severity,
                status=status,
                event_class=eventClass,
                tags=tags,
                element_sub_identifier=[""],
                )
        else:
            eventFilter = self.createEventFilter(
                severity=severity,
                status=status,
                event_class=eventClass,
                tags=tags,
                )

        response, content = self.client.getEventTagSeverities(from_dict(EventFilter, eventFilter))
        return content.severities

    def getDevicePingIssues(self):
        return self.getDeviceIssues(eventClass=[Status_Ping],
                                    severity=[SEVERITY_WARNING,SEVERITY_ERROR,SEVERITY_CRITICAL],
                                    status=[STATUS_NEW,STATUS_ACKNOWLEDGED,STATUS_SUPPRESSED])

    def getDeviceStatusIssues(self):
        return self.getDeviceIssues(eventClass=["/Status/"],
                                    severity=[SEVERITY_ERROR,SEVERITY_CRITICAL],
                                    status=[STATUS_NEW,STATUS_ACKNOWLEDGED])

    def getDeviceIssues(self, eventClass=(),
                        severity=(SEVERITY_DEBUG, SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL),
                        status=(STATUS_NEW,)):
        tagSeverities = self._getEventTagSeverities(
                eventClass=eventClass, severity=severity, status=status, deviceOnly=True)
        issues = []
        for eventTagSeverity in tagSeverities:
            device = self._guidManager.getObject(eventTagSeverity.tag_uuid)
            if device and isinstance(device, Device):
                count = 0
                for severity in eventTagSeverity.severities:
                    count += severity.count
                total = eventTagSeverity.total
                issues.append((device.id, count, total))
        return issues

    def getDeviceIssuesDict(self, eventClass=(), severity=(), status=()):
        severities = self._getEventTagSeverities(eventClass, severity, status)
        return self._createSeveritiesDict(severities)

    def getDetails(self):
        """
        Retrieve all of the indexed detail items.

        @rtype list of EventDetailItem dicts
        """
        return getDetailsInfo().getDetails()

    def getUnmappedDetails(self):
        """
        Return only non-zenoss details. This is used to get details that will not be mapped to another key.
        (zenoss.device.production_state maps back to prodState, so will be excluded here)
        """
        return getDetailsInfo().getUnmappedDetails()

    def getDetailsMap(self):
        """
        Return a mapping of detail keys to dicts of detail items
        """
        return getDetailsInfo().getDetailsMap()

    def parseParameterDetails(self, parameters):
        """
        Given grid parameters, split into keys that are details and keys that are other parameters.
        """

        params = {}
        details = {}

        detail_keys = self.getDetailsMap().keys()
        for k, v in parameters.iteritems():

            if k in self.ZENOSS_DETAIL_OLD_TO_NEW_MAPPING:
                k = self.ZENOSS_DETAIL_OLD_TO_NEW_MAPPING[k]

            if k in detail_keys:
                details[k] = v
            else:
                params[k] = v

        # verify parameters against known valid ones
        # If there's an extra, it either needs to be added or
        # is an invalid detail that can't be searched.
        leftovers = set(s.lower() for s in params) - set(self.DEFAULT_SORT_MAP) - set(('tags',
                                                                                       'deviceclass',
                                                                                       'systems',
                                                                                       'location',
                                                                                       'devicegroups',
                                                                                       'message',
                                                                                       'excludenonactionables'
                                                                                       ))
        if leftovers:
            raise InvalidQueryParameterException("Invalid query parameters specified: %s" % ', '.join(leftovers))


        return params, details


    def addIndexedDetails(self, detailItemSet):
        """
        @type detailItemSet: zenoss.protocols.protobufs.zep_pb2.EventDetailItemSet
        """
        _ZEP_DETAILS_INFO = []
        return self.configClient.addIndexedDetails(detailItemSet)

    def updateIndexedDetail(self, item):
        """
        @type item: zenoss.protocols.protobufs.zep_pb2.EventDetailItem
        """
        _ZEP_DETAILS_INFO = []
        return self.configClient.updateIndexedDetail(item)

    def removeIndexedDetail(self, key):
        """
        @type key: string
        """
        # Gather the new details information
        _ZEP_DETAILS_INFO = []
        return self.configClient.removeIndexedDetail(key)

    def countEventsSince(self, since):
        """
        Returns the total number of events in summary and archive that have been
        seen since the specified time (in seconds).

        @type  since: int
        @param since: Time (in seconds) from the epoch.
        @rtype:       int
        @return:      The number of events in summary and archive that have been seen
                      since the specified time.
        """
        sinceInMillis = int(since * 1000)
        eventFilter = self.createEventFilter(last_seen=[sinceInMillis])
        total = self.getEventSummaries(0, filter=eventFilter, limit=0)['total']
        total += self.getEventSummariesFromArchive(0, filter=eventFilter, limit=0)['total']
        return total

    def getHeartbeats(self, monitor=None):
        response, heartbeats = self.heartbeatClient.getHeartbeats(monitor=monitor)
        heartbeats_dict = to_dict(heartbeats)
        return heartbeats_dict.get('heartbeats', [])

    def deleteHeartbeats(self, monitor=None):
        self.heartbeatClient.deleteHeartbeats(monitor=monitor)

    def deleteHeartbeat(self, monitor, daemon):
        """
        Removes the heartbeat record for the specified monitor and daemon.

        @param monitor: The heartbeat monitor (i.e. 'localhost').
        @type monitor: basestring
        @param daemon: The heartbeat daemon (i.e. 'zenhub').
        @type daemon: basestring
        """
        self.heartbeatClient.deleteHeartbeat(monitor, daemon)

    def create(self, summary, severity, device, component=None, mandatory=True,
               **kwargs):
        """
        Create an event.

        @param summary: Summary message of the event. This variable gets mapped to an
            C{Event} protobuf field of the same name.
        @type summary: string

        @param severity: Severity name of the event. This variable gets mapped to the
            C{Event} protobuf using an C{EventProtobufSeverityMapper}
            (C{Products.ZenMessaging.queuemessaging.adapters.EventProtobufSeverityMapper}).
            This value can be an integer-like string value 0-5 or the string of the
            severity (clear, debug, info, warning, error, critical). The casing of the
            string does not matter. An empty severity value will be mapped to CLEAR.
        @type severity: string

        @param device: Device string. This variable gets set as the element on the
            C{Event} protobuf using an C{EventProtobufDeviceMapper}
            (C{Products.ZenMessaging.queuemessaging.adapters.EventProtobufDeviceMapper}).
            The value for this variable will always be set as a DEVICE element type.
            This value is later interpreted by zeneventd during the C{IdentifierPipe}
            (C{Products.ZenEvents.events2.processing.IdentifierPipe}) segment of the
            event processing pipeline. If an ipAddress is also provided in kwargs,
            the ipAddress is also used to help identify the device. If the ipAddress
            is provided, it is used first. If the ipAddress is not provided, the IP
            for a device is attempted to be discerned from the value of this variable.
            If the IP cannot be inferred, identification falls back to the value of
            this variable as either the ID of the device, or the title of the device
            as stored in the device catalog (as the NAME field).
        @type device: string

        @param component: ID of the component. This variable is used to lookup components
            by their ID or the title of the component (also stored as the NAME field in
            the catalog). See more info on how these objects are cataloged here:
            C{Products.Zuul.catalog.global_catalog.IndexableWrapper}.
        @type component: string

        @param mandatory:  If True, message will be returned unless it can be routed to
            a queue.
        @type mandatory: boolean
        @param eventClass: Name of the event class to fall under.
        @type eventClass: string

        For other parameters see class Event.
        """
        occurrence_uuid = str(uuid4())
        rcvtime = time()
        args = dict(evid=occurrence_uuid, summary=summary, severity=severity, device=device)
        if component:
            args['component'] = component
        args.update(kwargs)
        event = ZenEvent(rcvtime=rcvtime, **args)
        publisher = getUtility(IEventPublisher)
        publisher.publish(event, mandatory=mandatory)

    def updateDetails(self, evid, **detailInfo):
        """
        Given an evid, update the detail key/value pairs in ZEP.
        """

        if len(detailInfo) == 1 and isinstance(detailInfo.values()[0], EventDetailSet):
            return self.client.updateDetails(evid, detailInfo.values()[0])

        detailSet = EventDetailSet()
        for key, value in detailInfo.items():
            detailSet.details.add(name=key, value=(value,))

        return self.client.updateDetails(evid, detailSet)

    def getStats(self):
        response, stats = self.statsClient.get()
        statsList = []
        for stat in stats.stats:
            myst = {}
            myst['name'] = stat.name
            myst['description'] = stat.description
            myst['value'] = stat.value
            statsList.append(myst)
        return statsList



class ZepDetailsInfo:
    """
    Contains information about the indexed event details on ZEP.
    """

    def __init__(self):
        config = getGlobalConfiguration()
        schema = getUtility(IQueueSchema)
        zep_url = config.get('zep-uri', 'http://localhost:8084')
        self._configClient = ZepConfigClient(zep_url, schema)
        self._initialized = False

    def _initDetails(self):
        self._sortMap = dict(ZepFacade.DEFAULT_SORT_MAP)
        response, content = self._configClient.getDetails()

        detailsResponseDict = to_dict(content)
        self._details = detailsResponseDict.get('details', [])
        self._unmappedDetails = []
        self._detailsMap = {}
        for detail_item in self._details:
            detailKey = detail_item['key']
            sortField = { 'field': EventSort.DETAIL, 'detail_key': detailKey }
            mappedName = ZepFacade.ZENOSS_DETAIL_NEW_TO_OLD_MAPPING.get(detailKey, None)
            # If we have a mapped name, add it to the sort map to support sorting using old or new names
            if mappedName:
                self._sortMap[mappedName.lower()] = sortField
            else:
                self._unmappedDetails.append(detail_item)
            self._sortMap[detailKey.lower()] = sortField
            self._detailsMap[detailKey] = detail_item
        self._initialized = True

    def reload(self):
        """
        Reloads the event details configuration from ZEP.
        """
        self._initialized = False
        self._initDetails()

    def getDetails(self):
        """
        Retrieve all of the indexed detail items.

        @rtype list of EventDetailItem dicts
        """
        if not self._initialized:
            self._initDetails()
        return self._details

    def getUnmappedDetails(self):
        """
        Return only non-zenoss details. This is used to get details that will not be mapped to another key.
        (zenoss.device.production_state maps back to prodState, so will be excluded here)
        """
        if not self._initialized:
            self._initDetails()
        return self._unmappedDetails

    def getDetailsMap(self):
        """
        Return a mapping of detail keys to dicts of detail items
        """
        if not self._initialized:
            self._initDetails()
        return self._detailsMap

    def getSortMap(self):
        """
        Returns a mapping of a lowercase event field name to a dictionary which can be used
        to build the EventSort object to pass to ZEP.
        """
        if not self._initialized:
            self._initDetails()
        return self._sortMap

# Lazy-loaded cache of event details from ZEP
_ZEP_DETAILS_INFO = []
def getDetailsInfo():
    if not _ZEP_DETAILS_INFO:
        _ZEP_DETAILS_INFO.append(ZepDetailsInfo())
    return _ZEP_DETAILS_INFO[0]
