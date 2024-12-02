##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Operations for Events.

Available at:  /zport/dmd/evconsole_router
"""

import logging
import re
import time
from dateutil.parser import parse as parse_to_dt
from json import loads, dumps
from lxml.html.clean import clean_html
from zenoss.protocols.exceptions import NoConsumersException, PublishException
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_ACKNOWLEDGED
from zenoss.protocols.services import ServiceResponseError
from AccessControl import getSecurityManager
from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import require, serviceConnectionError
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from Products.ZenEvents.EventClass import EventClass
from Products.ZenMessaging.audit import audit
from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGE_EVENTS,
    ZEN_MANAGER_ROLE,
    MANAGER_ROLE
)
from Products.ZenUtils.deprecated import deprecated
from Products.Zuul.utils import resolve_context
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.Zuul.utils import get_dmd
from Products.ZenUI3.browser.eventconsole.grid import column_config
from Products.ZenUI3.security.security import permissionsForContext
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.infos.event import EventCompatInfo, EventCompatDetailInfo

READ_WRITE_ROLES = ['ZenManager', 'Manager', 'ZenOperator']

ZEN_MANAGER_EDIT_PERM = (
    'event_age_disable_severity',
    'event_age_interval_minutes',
    'event_archive_interval_minutes',
    'event_age_severity_inclusive',
    'default_syslog_priority',
    'default_trap_filtering_definition',
    'syslog_parsers',
    'syslog_summary_to_message',
    'default_syslog_message_filtering_rules',
    'default_availability_days',
    'event_time_purge_interval_days',
    'enable_event_flapping_detection',
    'flapping_event_class',
)

log = logging.getLogger('zen.%s' % __name__)

class _FilterParser(object):
    """
    Parses the filter related params received from the ui to search
    for "or clauses", "NULLs" and "NOTs"
    """

    NOT_SEPARATOR = "!!"
    OR_SEPARATOR = "||"
    NULL_CHAR='""'

    def __init__(self, zep_facade):
        """ """
        # Gets some config params from the zep facade
        detail_list =  zep_facade.getDetailsMap().keys()
        param_to_detail_mapping = zep_facade.ZENOSS_DETAIL_OLD_TO_NEW_MAPPING
        null_numeric_detail_value = zep_facade.ZENOSS_NULL_NUMERIC_DETAIL_INDEX_VALUE
        null_text_detail_value = zep_facade.ZENOSS_NULL_TEXT_DETAIL_INDEX_VALUE
        numeric_details = [ d['key'] for d in zep_facade.getDetails() if d['type'] == 2 ]

        # Sets config variables
        self.PARSEABLE_PARAMS = [ 'device', 'component', 'eventClass', 'ownerid', 'summary', 'message', 'monitor',
                                  'agent', 'eventClassKey', 'eventGroup', 'eventKey', 'dedupid', 'evid' ]
        self.PARAM_TO_FIELD_MAPPING = { 'device': 'element_title',
                                        'component': 'element_sub_title',
                                        'eventClass': 'event_class',
                                        'ownerid': 'current_user_name',
                                        'summary': 'event_summary',
                                        'message' :'message',
                                        'monitor': 'monitor',
                                        'agent': 'agent',
                                        'eventClassKey': 'event_class_key',
                                        'eventGroup': 'event_group',
                                        'eventKey': 'event_key',
                                        'dedupid': 'fingerprint',
                                        'evid': 'uuid' }
        self.PARSEABLE_DETAILS = detail_list
        self.PARAM_TO_DETAIL_MAPPING = param_to_detail_mapping
        for detail in self.PARSEABLE_DETAILS:
            if detail not in self.PARAM_TO_DETAIL_MAPPING.values():
                self.PARAM_TO_DETAIL_MAPPING[detail] = detail
        self.TRANSLATE_NULL = self.PARAM_TO_DETAIL_MAPPING.values()
        self.EXCLUDABLE = self.PARSEABLE_PARAMS + self.PARAM_TO_DETAIL_MAPPING.keys()
        self.NULL_NUMERIC_INDEX = null_numeric_detail_value
        self.NULL_TEXT_INDEX = null_text_detail_value
        self.NO_FRONT_WILDCARD = [ 'device', 'component', 'eventClass' ]
        self.NUMERIC_DETAILS = numeric_details
        self.NO_WILDCARD = self.NUMERIC_DETAILS[:]

    def findExclusionParams(self, params):
        """
        Look for filter params that contain the NOT_SEPARATOR
        @type  params: dictionary
        @param params: dictionary containing filter parameters from the ui
        @return: dictionary with the params that must be NOT filtered
        """
        exclude_params = {}
        if params is not None and isinstance(params, dict) and len(params) > 0:
            for param in self.EXCLUDABLE:
                value = params.get(param)
                if value is not None and isinstance(value, basestring) and self.NOT_SEPARATOR in value:
                    value = self._cleanText(value)
                    clauses = value.split(self.NOT_SEPARATOR)
                    inclusion_clause = clauses[0].strip()
                    exclusion_clause = clauses[1].strip()

                    if len(exclusion_clause) > 0:
                        exclude_params[param] = exclusion_clause
                    if len(inclusion_clause) == 0:
                        del params[param]
                    else:
                        params[param] = inclusion_clause

        return exclude_params

    def _cleanText(self, clause):
        """ """
        clause = re.sub('\s+', ' ', clause)
        clause = clause.strip(' *')
        return clause

    def _addWildcardsToFilter(self, field, value):
        """ """
        filter = value.strip()
        if filter != self.NULL_CHAR and field not in self.NO_WILDCARD:
            if field in self.NO_FRONT_WILDCARD:
                filter = '{0}*'.format(filter.strip())
            else:
                filter = '*{0}*'.format(filter.strip())

        return filter

    def _getOrClauses(self, field, value):
        """
        Given a filter field value, check if it contains the OR_SEPARATOR.
        @type  field: string
        @param field: name of the field
        @type  value: string
        @param value: field value received from the UI
        @return: list of OR clauses
        """
        or_clauses = []

        if isinstance(value, basestring):
            value = self._cleanText(value)
            if self.OR_SEPARATOR in value:
                temp_or_clauses = value.split(self.OR_SEPARATOR)
                or_clauses = [ self._addWildcardsToFilter(field, clause) for clause in temp_or_clauses if len(clause)>0 and clause != ' ']
            elif field in self.TRANSLATE_NULL and self.NULL_CHAR in value:
                or_clauses.append(self.NULL_CHAR)
            else:
                or_clauses.append(self._addWildcardsToFilter(field, value))
        elif isinstance(value, list):
            or_clauses = value

        # For details we need to translate the NULL_CHAR to the value used to index null
        # details in lucene.
        # The value used to index null details is different depending on if the detail
        # is numeric or text
        if len(or_clauses) > 0 and field in self.TRANSLATE_NULL:
            null_index = self.NULL_NUMERIC_INDEX if field in self.NUMERIC_DETAILS else self.NULL_TEXT_INDEX
            or_clauses = [ null_index if self.NULL_CHAR in str(c) else c for c in or_clauses ]

        return or_clauses

    def parseParams(self, params):
        """
        Parses the filter params passed from the UI looking
        for OR clauses or NULL values
        @type  params: dictionary
        @param params: dict of filter params passed from the UI
        @return
        """
        parsed_params = {}
        for par in self.PARSEABLE_PARAMS:
            if params.get(par) is not None:
                value = params.get(par)
                or_clauses = self._getOrClauses(field=par, value=value)
                filter_param = self.PARAM_TO_FIELD_MAPPING[par]
                parsed_params[filter_param] = or_clauses
        return parsed_params

    def parseDetails(self, details):
        """
        Parses the filter details passed from the UI looking
        for OR clauses or NULL values
        @type  details: dictionary
        @param details: dict of filter details passed from the UI
        @return
        """
        parsed_details = {}
        for detail in self.PARSEABLE_DETAILS:
            if details.get(detail) is not None:
                detail_value = details.get(detail)
                or_clauses = self._getOrClauses(field=detail, value=detail_value)
                parsed_details[detail] = or_clauses
        return parsed_details

class EventsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on events in ZEP
    """

    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.zep = Zuul.getFacade('zep', context)
        self.catalog = IModelCatalogTool(context)
        self.manager = IGUIDManager(context.dmd)
        self._filterParser = _FilterParser(self.zep)
        self.use_permissions = False

    def _canViewEvents(self):
        """
        To view any events you either have to have administered roles or
        be a global roled user
        """
        user = self.context.dmd.ZenUsers.getUserSettings()
        if not user.hasNoGlobalRoles():
            return True
        # make sure they have view permission on something
        if len(user.getAllAdminRoles()) > 0:
            self.use_permissions = True
        return len(user.getAllAdminRoles()) > 0

    def _timeRange(self, value):
        try:
            values = []
            splitter = ' TO ' if ' TO ' in value else '/'
            for t in value.split(splitter):
                values.append(float(t))
            return values
        except ValueError:
            log.warning("Invalid timestamp: %s", value)
            return ()
        except AttributeError:
            if isinstance(value, dict):
                return [float(parse_to_dt(value["dateFrom"]).strftime("%s"))*1000.0,
                        float(parse_to_dt(value["dateTo"]).strftime("%s"))*1000.0]


    def _filterInvalidUuids(self, events):
        """
        When querying archived events we need to make sure that
        we do not link to devices and components that are no longer valid
        """
        manager = self.manager
        for event_summary in events:
            occurrence = event_summary['occurrence'][0]
            actor = occurrence['actor']
            # element
            if actor.get('element_uuid') and \
                   actor.get('element_uuid') not in manager.table:
                del actor['element_uuid']

            # sub element
            if actor.get('element_sub_uuid') and \
                   actor.get('element_sub_uuid') not in manager.table:
                del actor['element_sub_uuid']
            yield event_summary

    @serviceConnectionError
    @require('ZenCommon')
    def queryArchive(self, page=None, limit=0, start=0, sort='lastTime', dir='desc', params=None, exclusion_filter=None, keys=None, uid=None, detailFormat=False):
        if not self._canViewEvents():
            return DirectResponse.succeed(
                events = [],
                totalCount = 0,
                asof = time.time()
                )

        exclude_params = self._filterParser.findExclusionParams(params)
        if len(exclude_params) > 0:
            if exclusion_filter is None:
                exclusion_filter = exclude_params
            else:
                exclusion_filter.update(exclude_params)

        filter = self._buildFilter([uid], params)
        if exclusion_filter is not None:
            exclusion_filter = self._buildFilter([uid], exclusion_filter)
        events = self.zep.getEventSummariesFromArchive(limit=limit, offset=start, sort=self._buildSort(sort,dir),
                                                       filter=filter, exclusion_filter=exclusion_filter)
        eventFormat = EventCompatInfo
        if detailFormat:
            eventFormat = EventCompatDetailInfo

        dmd = self.context.dmd
        # filter out the component and device UUIDs that no longer exist in our system
        evdata = self._filterInvalidUuids(events['events'])
        eventObs = [eventFormat(dmd, e) for e in evdata]
        return DirectResponse.succeed(
            events = Zuul.marshal(eventObs, keys),
            totalCount = events['total'],
            asof = time.time()
        )

    @serviceConnectionError
    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='desc', params=None, exclusion_filter=None, keys=None,
              page=None, archive=False, uid=None, detailFormat=False):
        """
        Query for events.

        @type  limit: integer
        @param limit: (optional) Max index of events to retrieve (default: 0)
        @type  start: integer
        @param start: (optional) Min index of events to retrieve (default: 0)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to search the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        if not self._canViewEvents():
            return DirectResponse.succeed(
                events = [],
                totalCount = 0,
                asof = time.time()
                )

        if archive:
            return self.queryArchive(limit=limit, start=start, sort=sort,
                                     dir=dir, params=params, exclusion_filter=exclusion_filter, keys=keys, uid=uid,
                                     detailFormat=detailFormat)

        def child_uids(org):
            """Return list of uids for children of Organizer org."""
            return [x.getPrimaryId() for x in org.children()]

        # Events don't get tagged with the top-level organizers. We compensate
        # for that here so that the events view for Devices, Groups, Systems,
        # and Locations will show aggregation of all of the top-level
        # organizers children.
        uids = {
            '/zport/dmd/Devices': child_uids(self.context.dmd.Devices),
            '/zport/dmd/Locations': child_uids(self.context.dmd.Locations),
            '/zport/dmd/Groups': child_uids(self.context.dmd.Groups),
            '/zport/dmd/Systems': child_uids(self.context.dmd.Systems),
            }.get(uid, [uid])

        exclude_params = self._filterParser.findExclusionParams(params)
        if len(exclude_params) > 0:
            if exclusion_filter is None:
                exclusion_filter = exclude_params
            else:
                exclusion_filter.update(exclude_params)

        filter = self._buildFilter(uids, params)
        if exclusion_filter is not None:
            exclusion_filter = self._buildFilter(uids, exclusion_filter)
        events = self.zep.getEventSummaries(limit=limit, offset=start, sort=self._buildSort(sort,dir), filter=filter,
                                            exclusion_filter=exclusion_filter, use_permissions=self.use_permissions)
        eventFormat = EventCompatInfo
        if detailFormat:
            eventFormat = EventCompatDetailInfo

        dmd = self.context.dmd
        # filter out the component and device UUIDs that no longer exist in our system
        evdata = self._filterInvalidUuids(events['events'])
        eventObs = [eventFormat(dmd, e) for e in evdata]

        return DirectResponse.succeed(
            events = Zuul.marshal(eventObs, keys),
            totalCount = events['total'],
            asof = time.time()
        )


    @serviceConnectionError
    @require('ZenCommon')
    def queryGenerator(self, sort='lastTime', dir='desc', evids=None, excludeIds=None, params=None,
                       archive=False, uid=None, detailFormat=False):
        """
        Query for events.

        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  archive: boolean
        @param archive: (optional) True to search the event archive instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @rtype:   generator
        @return:  Generator returning events.
        """

        if isinstance(params, basestring):
            params = loads(params)

        if not self._canViewEvents():
            return
        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)

        events = self.zep.getEventSummariesGenerator(filter=includeFilter, exclude=excludeFilter,
                                                      sort=self._buildSort(sort,dir), archive=archive)
        eventFormat = EventCompatInfo
        if detailFormat:
            eventFormat = EventCompatDetailInfo
        for event in events:
            yield Zuul.marshal(eventFormat(self.context.dmd, event))

    def _buildSort(self, sort='lastTime', dir='desc'):
        sort_list = [(sort,dir)]
        # Add secondary sort of last time descending
        if sort not in ('lastTime','evid'):
            sort_list.append(('lastTime','desc'))
        return sort_list


    def _buildFilter(self, uids, params, specificEventUuids=None, includeContextInUid=True):
        """
        Construct a dictionary that can be converted into an EventFilter protobuf.

        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uids: iterable(string)
        @param uids: (optional) Contexts for the query (default: None)
        """
        if not uids:
            uids=[]
        elif isinstance(uids, basestring):
            uids = [uids]

        if params:
            log.debug('logging params for building filter: %s', params)
            if isinstance(params, basestring):
                params = loads(params)

            # params comes from the grid's filtering column -
            # some of these properties are normal properties on an event
            # while others are considered event details. Separate the
            # two here.
            params, details = self.zep.parseParameterDetails(params)

            filterEventUuids = []
            # No specific event uuids passed in-
            # check for event ids from the grid parameters
            if specificEventUuids is None:
                log.debug('No specific event uuids were passed in.')

                # The evid's from params only ever mean anything for filtering - if
                # specific uuids are passed in, this filter will ignore the grid
                # parameters and just act on or filter using these specific event uuids.
                evid = params.get('evid')
                if evid:
                    if not isinstance(evid,(list, tuple)):
                        evid = [evid]
                    filterEventUuids.extend(evid)

            # Specific event uuids were passed in, use those for this filter.
            else:
                log.debug('Specific event uuids passed in: %s', specificEventUuids)
                if not isinstance(specificEventUuids,(list, tuple)):
                    filterEventUuids = [specificEventUuids]
                else:
                    filterEventUuids = specificEventUuids

            log.debug('FilterEventUuids is: %s', filterEventUuids)

            # 'tags' comes from managed object guids.
            # see Zuul/security/security.py
            param_tags = params.get('tags')
            if params.get('excludeNonActionables') and not Zuul.checkPermission(ZEN_MANAGE_EVENTS, self.context):
                if not param_tags:
                    us = self.context.dmd.ZenUsers.getUserSettings()
                    param_tags = [IGlobalIdentifier(ar.managedObject()).getGUID() for ar in us.getAllAdminRoles()]
                if param_tags:
                    param_tags = [tag for tag in param_tags if Zuul.checkPermission(ZEN_MANAGE_EVENTS, self.manager.getObject(tag))]
                if not param_tags:
                    param_tags = ['dne'] # Filter everything (except "does not exist'). An empty tag list would be ignored.

            status_filter = params.get('eventState', [])
            if params.get('eventStateText', None):
                status_filter = list(set(status_filter + params.get('eventStateText')))

            filter_params = {
                'severity': params.get('severity'),
                'status': status_filter,
                'event_class': filter(None, [params.get('eventClass')]),
                'first_seen': params.get('firstTime') and self._timeRange(params.get('firstTime')),
                'last_seen': params.get('lastTime') and self._timeRange(params.get('lastTime')),
                'status_change': params.get('stateChange') and self._timeRange(params.get('stateChange')),
                'uuid': filterEventUuids,
                'count_range': params.get('count'),
                'element_title': params.get('device'),
                'element_sub_title': params.get('component'),
                'event_summary': params.get('summary'),
                'current_user_name': params.get('ownerid'),
                'agent': params.get('agent'),
                'monitor': params.get('monitor'),
                'fingerprint': params.get('dedupid'),
                'tags': param_tags,
                'details': details,
                'event_key': params.get('eventKey'),
                'event_class_key': params.get('eventClassKey'),
                'event_group': params.get('eventGroup'),
                'message': params.get('message'),
            }
            parsed_params = self._filterParser.parseParams(params)
            # ZEN23418: Add 1 sec to first_seen and last_seen range filters,
            # so that it includes {events: event['{first|last}_seen'] <= params['{firstTime|lastTime}']}
            filter_params.update(parsed_params)
            if filter_params['first_seen'] is not None and len(filter_params['first_seen']) == 2:
                filter_params['first_seen'][1] = filter_params['first_seen'][1]+1000
            if filter_params['last_seen'] is not None and len(filter_params['last_seen']) == 2:
                filter_params['last_seen'][1] = filter_params['last_seen'][1]+1000

            parsed_details = self._filterParser.parseDetails(details)
            if len(parsed_details) > 0:
                filter_params['details'].update(parsed_details)

            event_filter = self.zep.createEventFilter(**filter_params)
            log.debug('Found params for building filter, ended up building  the following:')
            log.debug(event_filter)
        elif specificEventUuids:
            # if they passed in specific uuids but not other params
            event_filter = self.zep.createEventFilter(
                uuid = specificEventUuids
                )
        else:
            log.debug('Did not get parameters, using empty filter.')
            event_filter = {}

        if not uids and includeContextInUid:
            uids = [self.context]

        contexts = (resolve_context(uid) for uid in uids)

        context_uuids = []
        for context in contexts:
            if context and context.id not in ('Events', 'Devices', 'dmd'):
                try:
                    # make a specific instance of tag_filter just for the context tag.
                    if not context_uuids:
                        context_tag_filter = {
                            'tag_uuids': context_uuids
                            }
                        # if it exists, filter['tag_filter'] will be a list. just append the special
                        # context tag filter to whatever that list is.
                        tag_filter = event_filter.setdefault('tag_filter', [])
                        tag_filter.append(context_tag_filter)
                    context_uuids.append(IGlobalIdentifier(context).getGUID())

                except TypeError:
                    if isinstance(context, EventClass):
                        event_filter['event_class'] = [context.getDmdKey()]
                    else:
                        raise Exception('Unknown context %s' % context)

        log.debug('Final filter will be:')
        log.debug(event_filter)

        return event_filter

    def detail(self, evid):
        """
        Get event details.

        @type  evid: string
        @param evid: Event ID to get details
        @type  history: boolean
        @param history: Deprecated
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - event: ([dictionary]) List containing a dictionary representing
                    event details
        """
        event_summary = self.zep.getEventSummary(evid)
        if event_summary:
            eventData = Zuul.marshal(EventCompatDetailInfo(self.context.dmd, event_summary))
            return DirectResponse.succeed(event=[eventData])
        else:
            raise Exception('Could not find event %s' % evid)

    def _hasPermissionsForAllEvents(self, permission, evids):
        try:
            dmd = get_dmd()
            target_permission = permission.lower()
            events_filter = self._buildFilter(uids=None, params={}, specificEventUuids=evids)
            event_summaries = self.zep.getEventSummaries(0, filter=events_filter, use_permissions=True)
            devices = set()
            for summary in event_summaries['events']:
                d = EventCompatInfo(self.context.dmd, summary)
                dev_obj = dmd.getObjByPath(d.device['uid'])
                devices.add(dev_obj)
            for device in devices:
                if not permissionsForContext(device)[target_permission]:
                    return False
            return True
        except Exception as e:
            log.debug(e)
            return False

    def manage_events(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None, timeout=None):
        user = self.context.dmd.ZenUsers.getUserSettings()
        if Zuul.checkPermission(ZEN_MANAGE_EVENTS, self.context):
            return True
        if params:
            if params.get('excludeNonActionables', None):
                return Zuul.checkPermission('ZenCommon', self.context)
        try:
            if uid is not None:
                organizer = self.context.dmd.Devices.getOrganizer(uid)
            else:
                return self._hasPermissionsForAllEvents(ZEN_MANAGE_EVENTS, evids)
        except (AttributeError, KeyError):
            return False

        manage_events_for = []
        for r in user.getAllAdminRoles():
            if r.role in READ_WRITE_ROLES:
                role_managed_object = r.managedObject()
                for sub_org in role_managed_object.getSubOrganizers():
                    manage_events_for.append(
                        role_managed_object.getBreadCrumbUrlPath()
                    )
                    manage_events_for.append(
                        sub_org.getBreadCrumbUrlPath()
                    )

        return organizer.getBreadCrumbUrlPath() in manage_events_for

    def can_add_events(self, summary, device, component, severity, evclasskey,
                  evclass=None, monitor=None, **kwargs):
        ctx = self.context.dmd.Devices.findDevice(device.strip())
        if not ctx:
            ctx = self.context

        return Zuul.checkPermission(ZEN_MANAGE_EVENTS, ctx)

    def write_event_logs(self, evid=None, message=None):
        data = self.detail(evid).data['event'][0]
        uuid = data['component_uuid'] or data['device_uuid']
        if uuid is None:
            ctx = self.context
        else:
            ctx = self.manager.getObject(uuid)
        return Zuul.checkPermission(ZEN_MANAGE_EVENTS, ctx)

    @require(write_event_logs)
    def write_log(self, evid=None, message=None):
        """
        Write a message to an event's log.

        @type  evid: string
        @param evid: Event ID to log to
        @type  message: string
        @param message: Message to log
        @rtype:   DirectResponse
        @return:  Success message
        """

        userName = getSecurityManager().getUser().getId()

        self.zep.addNote(uuid=evid, message=clean_html(message), userName=userName)

        return DirectResponse.succeed()

    @require(ZEN_MANAGE_EVENTS)
    def postNote(self, uuid, note):
        self.zep.postNote(uuid, note)
        return DirectResponse.succeed()

    def _buildRequestFilters(self, uid, params, evids, excludeIds):
        """
        Given common request parameters, build the inclusive and exclusive
        filters for event update requests.
        """

        if uid is None and isinstance(self.context, EventClass):
            uid = self.context

        log.debug('Context while building request filters is: %s', uid)

        # if the request contains specific event summaries to act on, they will
        # be passed in as evids. Excluded event summaries are passed in under
        # the keyword argument 'excludeIds'. If these exist, pass them in as
        # parameters to be used to construct the EventFilter.
        includeUuids = None
        if isinstance(evids, (list, tuple)):
            log.debug('Found specific event ids, adding to params.')
            includeUuids = evids

        exclude_params = self._filterParser.findExclusionParams(params)
        includeFilter = self._buildFilter([uid], params, specificEventUuids=includeUuids)

        # the only thing excluded in an event filter is a list of event uuids
        # which are passed as EventTagFilter using the OR operator.
        excludeFilter = None
        if excludeIds or len(exclude_params) > 0:
            if excludeIds is None:
                excludeIds = {}
            # make sure the exclude filter doesn't include the context
            # otherwise all event actions wont have an effect.
            excludeFilter = self._buildFilter(None, exclude_params,
                                              specificEventUuids=excludeIds.keys(),
                                              includeContextInUid=False)

        log.debug('The exclude filter: %s', excludeFilter)
        log.debug('Finished building request filters.')

        return includeFilter, excludeFilter

    @require(ZEN_MANAGE_EVENTS)
    def nextEventSummaryUpdate(self, next_request):
        """
        When performing updates from the event console, updates are performed in batches
        to allow the user to see the progress of event changes and cancel out of updates
        while they are in progress. This works by specifying a limit to one of the close,
        acknowledge, or reopen calls in this router. The response will contain an
        EventSummaryUpdateResponse, and if there are additional updates to be performed,
        it will contain a next_request field with all of the parameters used to update
        the next range of events.

        @type  next_request: dictionary
        @param next_request: The next_request field from the previous updates.
        """
        log.debug('Starting next batch of updates')
        status, summaryUpdateResponse = self.zep.nextEventSummaryUpdate(next_request)

        log.debug('Completed updates: %s', summaryUpdateResponse)
        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require(ZEN_MANAGE_EVENTS)
    def clear_device_heartbeats(self, params, limit=None):
        """
        @type  params: dictionary
        @param params: Key-value pair of filters for this search.
        """
        if isinstance(params, basestring):
            params = loads(params)

        device = params['device']

        log.debug('Clearing heartbeats for device: %s', device)

        params['eventState'] = [STATUS_NEW, STATUS_ACKNOWLEDGED]
        params['eventClass'] = '/Status/Heartbeat'

        includeFilter, excludeFilter = self._buildRequestFilters(None, params, None, None)

        status, summaryUpdateResponse = self.zep.closeEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
        )

        log.debug('Done clearing heartbeats for device: %s', device)
        log.debug(summaryUpdateResponse)
        audit('UI.Device.ClearHeartbeats', device=device)

        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require(manage_events)
    def close(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None, timeout=None):
        """
        Close event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to close (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           close (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only close if there has been no state
                     change since this time (default: None)
        @type  limit: The maximum number of events to update in this batch.
        @param limit: (optional) Maximum number of events to update (default: None).
        @type  timeout: int
        @param timeout: The time (in seconds) before the underlying saved search times out.
        @rtype:   DirectResponse
        @return:  Success message
        """

        log.debug('Issuing a close request.')

        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)

        status, summaryUpdateResponse = self.zep.closeEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
            timeout=timeout,
        )

        log.debug('Done issuing close request.')
        log.debug(summaryUpdateResponse)

        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require(manage_events)
    def acknowledge(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None, timeout=None):
        """
        Acknowledge event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to acknowledge (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           acknowledgment (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only acknowledge if there has been no state
                     change since this time (default: None)
        @type  limit: The maximum number of events to update in this batch.
        @param limit: (optional) Maximum number of events to update (default: None).
        @type  timeout: int
        @param timeout: The time (in seconds) before the underlying saved search times out.
        @rtype:   DirectResponse
        @return:  Success message
        """
        log.debug('Issuing an acknowledge request.')

        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)

        status, summaryUpdateResponse = self.zep.acknowledgeEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
            timeout=timeout,
        )
        log.debug('Done issuing acknowledge request.')
        log.debug(summaryUpdateResponse)

        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require(manage_events)
    @deprecated
    def unacknowledge(self, *args, **kwargs):
        """
        Deprecated, Use reopen
        """
        return self.reopen(*args, **kwargs)

    @require(manage_events)
    def reopen(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None, timeout=None):
        """
        Reopen event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to reopen (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           reopen (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only reopen if there has been no state
                     change since this time (default: None)
        @type  limit: The maximum number of events to update in this batch.
        @param limit: (optional) Maximum number of events to update (Default: None).
        @type  timeout: int
        @param timeout: The time (in seconds) before the underlying saved search times out.
        @rtype:   DirectResponse
        @return:  Success message
        """

        log.debug('Issuing a reopen request.')

        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)

        status, summaryUpdateResponse = self.zep.reopenEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
            timeout=timeout,
        )

        log.debug('Done issuing reopen request.')
        log.debug(summaryUpdateResponse)

        return DirectResponse.succeed(data=summaryUpdateResponse)


    @require(ZEN_MANAGE_EVENTS)
    def updateEventSummaries(self, update, event_filter=None, exclusion_filter=None, limit=None, timeout=None):
        status, response = self.zep.updateEventSummaries(update, event_filter, exclusion_filter, limit, timeout=timeout)
        return DirectResponse.succeed(data=response)

    @require(can_add_events)
    def add_event(self, summary, device, component, severity, evclasskey,
                  evclass=None, monitor=None, **kwargs):
        """
        Create a new event.

        @type  summary: string
        @param summary: New event's summary
        @type  device: string
        @param device: Device id to use for new event
        @type  component: string
        @param component: Component uid to use for new event
        @type  severity: string
        @param severity: Severity of new event. Can be one of the following:
                         Critical, Error, Warning, Info, Debug, or Clear
        @type  evclasskey: string
        @param evclasskey: The Event Class Key to assign to this event
        @type  evclass: string
        @param evclass: Event class for the new event
        @rtype:   DirectResponse

        For other parameters please see class Event.
        """
        device = device.strip()  # ZEN-2479: support entries like "localhost "
        try:
            self.zep.create(summary, severity, device, component,
                            eventClassKey=evclasskey, eventClass=evclass,
                            monitor=monitor, **kwargs)
            return DirectResponse.succeed("Created event")
        except NoConsumersException:
            # This occurs if the event is queued but there are no consumers - i.e. zeneventd is not
            # currently running.
            msg = 'Queued event. Check zeneventd status on <a href="/zport/dmd/daemons">Services</a>'
            return DirectResponse.succeed(msg, sticky=True)
        except PublishException as e:
            # This occurs if there is a failure publishing the event to the queue.
            log.exception("Failed creating event")
            return DirectResponse.exception(e, "Failed to create event")

    @property
    def configSchema(self):
        configSchema =[{
                'id': 'event_age_disable_severity',
                'name': _t("Don't Age This Severity and Above"),
                'xtype': 'eventageseverity',
                },{
                'id': 'event_age_severity_inclusive',
                'xtype': 'hidden',
                },{
                'id': 'event_age_interval_minutes',
                'name': _t('Event Aging Threshold (minutes)'),
                'xtype': 'numberfield',
                'minValue': 0,
                'allowNegative': False,
                },{
                'id': 'aging_interval_milliseconds',
                'name': _t('Event Aging Interval (milliseconds)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'allowNegative': False
                },{
                'id': 'aging_limit',
                'name': _t('Event Aging Limit'),
                'xtype': 'numberfield',
                'minValue': 1,
                'allowNegative': False
                },{
                'id': 'event_archive_interval_minutes',
                'name': _t('Event Archive Threshold (minutes)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'maxValue': 43200,
                'allowNegative': False,
                },{
                'id': 'archive_interval_milliseconds',
                'name': _t('Event Archive Interval (milliseconds)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'allowNegative': False,
                },{
                'id': 'archive_limit',
                'name': _t('Event Archive Limit'),
                'xtype': 'numberfield',
                'minValue': 1,
                'allowNegative': False,
                },{
                'id': 'event_archive_purge_interval_days',
                'minValue': 1,
                'name': _t('Delete Archived Events Older Than (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                },{
                'id': 'default_syslog_priority',
                'name': _t('Default Syslog Priority'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'value': self.context.dmd.ZenEventManager.defaultPriority
                },{
                'id': 'default_trap_filtering_definition',
                'name': _t('SNMP Trap Filtering Rules'),
                'xtype': 'textarea',
                'allowNegative': False,
                'value': self.context.dmd.ZenEventManager.trapFilters
                },{
                'id': 'syslog_parsers',
                'name': _t('Syslog Parsers'),
                'xtype': 'textarea',
                'value': dumps(self.context.dmd.ZenEventManager.syslogParsers, indent=2)
                },{
                'id': 'syslog_summary_to_message',
                'name': _t('Mirror Syslog Event\'s Summary value to Message field'),
                'xtype': 'checkbox',
                'value': self.context.dmd.ZenEventManager.syslogSummaryToMessage
                },{
                'id': 'default_syslog_message_filtering_rules',
                'name': _t('Syslog Message Filtering Rules'),
                'xtype': 'textarea',
                'allowNegative': False,
                'value': dumps(self.context.dmd.ZenEventManager.syslogMsgEvtFieldFilterRules, indent=2)
                },{
                'id': 'default_availability_days',
                'name': _t('Default Availability Report (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1,
                'value': self.context.dmd.ZenEventManager.defaultAvailabilityDays
                },{
                'id': 'event_max_size_bytes',
                'name': _t('Max Event Size In Bytes'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 8192,
                'maxValue': 102400,
                },{
                'id': 'index_summary_interval_milliseconds',
                'name': _t('Summary Index Interval (milliseconds)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1
                },{
                'id': 'index_archive_interval_milliseconds',
                'name': _t('Archive Index Interval (milliseconds)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1
                },{
                'id': 'index_limit',
                'name': _t('Index Limit'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1
                },{
                'id': 'event_time_purge_interval_days',
                'name': _t('Event Time Purge Interval (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1
                },{
                'id': 'enable_event_flapping_detection',
                'name': _t('Enable Event Flapping Detection'),
                'xtype': 'checkbox',
                }, {
                'id': 'flapping_event_class',
                'name': _t('Event Flapping Event Class'),
                'xtype': 'eventclass'
                }]
        return configSchema

    def iseditable(self, field):
        currentUser = self.context.dmd.ZenUsers.getUser()
        if currentUser:
            if currentUser.has_role(MANAGER_ROLE):
                return True

            if currentUser.has_role(ZEN_MANAGER_ROLE) and field in ZEN_MANAGER_EDIT_PERM:
                return True

        return False

    def _mergeSchemaAndZepConfig(self, data, configSchema):
        """
        Copy the values and defaults from ZEP to our schema
        """
        for conf in configSchema:
            if not data.get(conf['id']):
                continue
            prop = data[conf['id']]
            conf.update(prop)
        return configSchema

    @require('ZenCommon')
    def getConfig(self):
        # this data var is not a ZepConfig, it's a config structure that has been
        # constructed to include default values and be keyed by the protobuf
        # property name.
        data = self.zep.getConfig()
        schema = self._mergeSchemaAndZepConfig(data, self.configSchema)
        config = [setting for setting in schema if self.iseditable(setting['id'])]
        return DirectResponse.succeed(data=config)

    @require('Manage DMD')
    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        # Remove empty strings from values
        empty_keys = [k for k,v in values.iteritems() if isinstance(v, basestring) and not len(v)]
        for empty_key in empty_keys:
            del values[empty_key]

        # we store default syslog priority and default availability days on the event manager
        defaultSyslogPriority = values.pop('default_syslog_priority', None)
        if defaultSyslogPriority is not None:
            self.context.dmd.ZenEventManager.defaultPriority = int(defaultSyslogPriority)

        trapFilters = values.pop('default_trap_filtering_definition', None)
        if trapFilters is not None:
            self.context.dmd.ZenEventManager.trapFilters = trapFilters

        syslogParsers = values.pop('syslog_parsers', None)
        if syslogParsers is not None:
            self.context.dmd.ZenEventManager.syslogParsers = loads(syslogParsers)

        syslogSummaryToMessage = values.pop('syslog_summary_to_message', None)
        if syslogSummaryToMessage is not None:
            self.context.dmd.ZenEventManager.syslogSummaryToMessage = syslogSummaryToMessage
        syslogMsgEvtFieldFilterRules = values.pop('default_syslog_message_filtering_rules', None)
        if syslogMsgEvtFieldFilterRules is not None:
            self.context.dmd.ZenEventManager.syslogMsgEvtFieldFilterRules = loads(syslogMsgEvtFieldFilterRules)

        defaultAvailabilityDays = values.pop('default_availability_days', None)
        if defaultAvailabilityDays is not None:
            self.context.dmd.ZenEventManager.defaultAvailabilityDays = int(defaultAvailabilityDays)

        # filter by role whether user can update settings.
        eventConfig = {key: value for (key, value) in values.items() if self.iseditable(key)}
        self.zep.setConfigValues(eventConfig)
        return DirectResponse.succeed()

    def column_config(self, uid=None, archive=False):
        """
        Get the current event console field column configuration.

        @type  uid: string
        @param uid: (optional) UID context to use (default: None)
        @type  archive: boolean
        @param archive: (optional) True to use the event archive instead
                        of active events (default: False)
        @rtype:   [dictionary]
        @return:  A list of objects representing field columns
        """
        return column_config(self.request, archive)

    @require(ZEN_MANAGE_EVENTS)
    def classify(self, evrows, evclass):
        """
        Associate event(s) with an event class.

        @type  evrows: [dictionary]
        @param evrows: List of event rows to classify
        @type  evclass: string
        @param evclass: Event class to associate events to
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - msg: (string) Success/failure message
           - success: (boolean) True if class update successful
        """
        msg, url = self.zep.createEventMapping(evrows, evclass)
        if url:
            msg += " | " + url.split('/dmd/')[1]
        audit('UI.Event.Classify', evrows, message=msg, event_class=evclass)
        return DirectResponse(msg, success=bool(url))

    @require(ZEN_MANAGE_EVENTS)
    def clear_heartbeats(self):
        """
        Clear all heartbeat events

        @rtype:   DirectResponse
        @return:  B{Properties}:
           - success: (boolean) True if heartbeats deleted successfully
        """
        self.zep.deleteHeartbeats()
        audit('UI.Event.ClearHeartbeats', self.context)
        return DirectResponse.succeed()

    @require(ZEN_MANAGE_EVENTS)
    def clear_heartbeat(self, monitor, daemon):
        """
        Clears a specific heartbeat event.

        @type monitor: basestring
        @param monitor: The heartbeat monitor (i.e. 'localhost').
        @type daemon: basestring
        @param daemon: The heartbeat daemon (i.e. 'zenhub').
        @rtype: DirectResponse
        @return: A DirectResponse indicating success or failure.
        """
        self.zep.deleteHeartbeat(monitor, daemon)
        audit('UI.Event.ClearHeartbeat', self.context, monitor=monitor,
              daemon=daemon)
        return DirectResponse.succeed()

    @require(ZEN_MANAGE_EVENTS)
    def updateDetails(self, evid, **detailInfo):
        """
        On success, returns the status.
        """
        try:
            resp = self.zep.updateDetails(evid, **detailInfo)
        except ServiceResponseError as ex:
            return DirectResponse.fail(msg=str(ex))
        audit('UI.Event.UpdateEventDetails', self.context, evid=evid,
              details=detailInfo)
        return DirectResponse.succeed(status=resp[0]['status'])
