##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenEvents.events2.fields import EventField
from Products.ZenEvents.interfaces import IEventIdentifierPlugin
from Products.ZenModel.Device import Device
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenEvents.events2.proxy import ZepRawEventProxy, EventProxy
from Products.ZenUtils.guid.interfaces import IGUIDManager, IGlobalIdentifier
from Products.ZenUtils.IpUtil import isip, ipToDecimal
from Products.ZenUtils.FunctionCache import FunctionCache
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.AdvancedQuery import Eq, Or
from zope.component import getUtility, getUtilitiesFor
from Acquisition import aq_chain
from Products.ZenEvents import ZenEventClasses
from itertools import ifilterfalse

from zenoss.protocols.jsonformat import to_dict
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_CLOSED,
    STATUS_DROPPED,
    )

import logging

log = logging.getLogger("zen.eventd")

class ProcessingException(Exception):
    def __init__(self, message, event=None):
        super(ProcessingException, self).__init__(message)
        self.event = event

class DropEvent(ProcessingException):
    """
    Raised when an event should be dropped from the queue.
    """
    pass

class EventLoggerAdapter(logging.LoggerAdapter):
    """
    A logging adapter that adds the event UUID to the log output.
    """

    def process(self, msg, kwargs):
        msg = '[{event_uuid}] {msg}'.format(event_uuid=self.extra['event_uuid'],
                                            msg=msg)
        return msg, kwargs

def quote_and_escape(value):
    return '"{}"'.format(value.replace('"', '\\"'))

class Manager(object):
    """
    Provides lookup access to processing pipes and performs caching.
    """

    ELEMENT_TYPE_MAP = {
        DEVICE: Device,
        COMPONENT: DeviceComponent,
    }

    def __init__(self, dmd):
        self.dmd = dmd
        self._initCatalogs()

    def _initCatalogs(self):
        self._guidManager = IGUIDManager(self.dmd)

        self._devices = self.dmd._getOb('Devices')
        self._networks = self.dmd._getOb('Networks')
        self._events = self.dmd._getOb('Events')

        self._catalogs = {
            DEVICE: self._devices,
        }

    def reset(self):
        self._initCatalogs()

    def getEventClassOrganizer(self, eventClassName):
        try:
            return self._events.getOrganizer(eventClassName)
        except KeyError:
            # Unknown organizer
            return None

    def lookupEventClass(self, eventContext):
        """
        Find a Device's EventClass
        """
        return self._events.lookup(eventContext.eventProxy,
                                   eventContext.deviceObject)

    def getElementByUuid(self, uuid):
        """
        Get a Device/Component by UUID
        """
        if uuid:
            return self._guidManager.getObject(uuid)

    def uuidFromBrain(self, brain):
        """
        Helper method to deal with catalog brains which are out of date. If
        the uuid is not set on the brain, we attempt to load it from the
        object.
        """
        uuid = brain.uuid
        return uuid if uuid else IGlobalIdentifier(brain.getObject()).getGUID()

    @FunctionCache("getElementUuidById", cache_miss_marker=-1, default_timeout=300)
    def getElementUuidById(self, catalog, element_type_id, id):
        """
        Find element by ID but only cache UUID. This forces us to lookup elements
        each time by UUID (pretty fast) which gives us a chance to see if the element
        has been deleted.
        """
        cls = self.ELEMENT_TYPE_MAP.get(element_type_id)
        if cls:
            catalog = catalog or self._catalogs.get(element_type_id)
            if catalog:
                quoted_id = quote_and_escape(id)
                results = IModelCatalogTool(catalog).search(cls,
                                                       query=Or(Eq('id', quoted_id),
                                                                Eq('name', quoted_id)),
                                                       filterPermissions=False,
                                                       limit=1, fields=["uuid"])
                if results.total:
                    try:
                        result = results.results.next()
                    except StopIteration:
                        pass
                    else:
                        return self.uuidFromBrain(result)

    def getElementById(self, catalog, element_type_id, id):
        """
        Find element by ID, first checking a cache for UUIDs then using that UUID
        to load the element. If the element can't be found by UUID, the UUID
        cache is cleared and lookup tried again.
        """
        uuid = self.getElementUuidById(catalog, element_type_id, id)
        if uuid:
            element = self.getElementByUuid(uuid)
            if not element:
                # Lookup cache must be invalid, try looking up again
                self.getElementUuidById.clear()
                log.warning(
                        'Clearing ElementUuidById cache becase we could not find %s', uuid)
                uuid = self.getElementUuidById(catalog, element_type_id, id)
                element = self.getElementByUuid(uuid)
            return element

    def getElementUuid(self, obj):
        if obj:
            return IGlobalIdentifier(obj).getGUID()

    def _findDevices(self, identifier, ipAddress, limit=None):
        """
        Returns a tuple ([device brains], [devices]) searching manage IP and
        interface IPs. limit is the maximum total number in both lists.
        """
        dev_cat = IModelCatalogTool(self._devices)

        try:
            ip_address = next(i for i in (ipAddress, identifier) if isip(i))
            ip_decimal = ipToDecimal(ip_address)
        except Exception:
            ip_address = None
            ip_decimal = None

        quoted_id = quote_and_escape(identifier)
        query_set = Or(Eq('id', quoted_id), Eq('name', quoted_id))
        if ip_decimal is not None:
            query_set.addSubquery(Eq('decimal_ipAddress', str(ip_decimal)))
        device_brains = list(dev_cat.search(types=Device,
                                            query=query_set,
                                            limit=limit,
                                            filterPermissions=False,
                                            fields=["uid", "uuid"]))

        if device_brains:
            return device_brains, []

        if ip_decimal is not None:
            # don't search interfaces for 127.x.x.x IPv4 addresses
            if ipToDecimal('126.255.255.255') < ip_decimal < ipToDecimal('128.0.0.0'):
                ip_decimal = None
            # don't search interfaces for the ::1 IPv6 address
            elif ipToDecimal('::1') == ip_decimal:
                ip_decimal = None
        if ip_decimal is None:
            return [], []

        net_cat = IModelCatalogTool(self._networks)
        results = net_cat.search(types=IpAddress,
                                 query=(Eq('name', ip_address)),
                                 limit = limit,
                                 filterPermissions = False)
        devices = [brain.getObject().device() for brain in results]

        return device_brains, devices

    @FunctionCache("findDeviceUuid", cache_miss_marker=-1, default_timeout=300)
    def findDeviceUuid(self, identifier, ipAddress):
        """
        This will return the device's
        @type  identifier: string
        @param identifier: The IP address or id of a device
        @type  ipaddress: string
        @param ipaddress: The known ipaddress of the device
        """
        device_brains, devices = self._findDevices(identifier, ipAddress, limit=1)
        if device_brains:
            return self.uuidFromBrain(device_brains[0])
        if devices:
            return self.getElementUuid(devices[0])
        return None

    def findDevice(self, identifier, ipAddress):
        uuid = self.findDeviceUuid(identifier, ipAddress)
        if uuid:
            return self.getElementByUuid(uuid)

    def getUuidsOfPath(self, node):
        """
        Looks up all the UUIDs in the tree path of an Organizer
        """
        uuids = set()
        acquisition_chain = []
        for n in aq_chain(node.primaryAq()):
            if isinstance(n, DataRoot):
                acquisition_chain.pop()
                break
            acquisition_chain.append(n)

        if acquisition_chain:
            for obj in filter(None, acquisition_chain):
                try:
                    uuids.add(self.getElementUuid(obj))
                except TypeError:
                    log.debug("Unable to get a uuid for %s ", obj)

        return filter(None, uuids)


class EventContext(object):
    """
    Maintains the event context while processing.
    """

    def __init__(self, log, zepRawEvent):
        self._zepRawEvent = zepRawEvent
        self._event = self._zepRawEvent.event
        self._eventProxy = ZepRawEventProxy(self._zepRawEvent)

        # If this event is for a device, it will be attached here
        self._deviceObject = None
        self._componentObject = None
        self.log = EventLoggerAdapter(log, {'event_uuid': self._event.uuid})

    def setDeviceObject(self, device):
        self._deviceObject = device

    def refreshClearClasses(self):
        self._eventProxy._refreshClearClasses()

    @property
    def deviceObject(self):
        return self._deviceObject

    def setComponentObject(self, component):
        self._componentObject = component

    @property
    def componentObject(self):
        return self._componentObject

    @property
    def zepRawEvent(self):
        return self._zepRawEvent

    @property
    def event(self):
        return self._event

    @property
    def eventProxy(self):
        """
        A EventProxy that wraps the event protobuf and makes it look like an old style event.
        """
        return self._eventProxy

class EventProcessorPipe(object):
    """
    An event context handler that is called in a chain.
    """
    dependencies = []

    def __init__(self, manager, name=None):
        self._manager = manager
        if name:
            self.name = name
        else:
            self.name = self.__class__.__name__

    def __call__(self, eventContext):
        """
        Called in a chain, must return modified eventContext.
        """
        raise NotImplementedError()

class CheckInputPipe(EventProcessorPipe):
    """
    Validates that the event has required fields.
    """
    REQUIRED_EVENT_FIELDS = (
    EventField.ACTOR, EventField.SUMMARY, EventField.SEVERITY)

    def __call__(self, eventContext):

        # Make sure summary and message are populated
        if not eventContext.event.HasField(
                'message') and eventContext.event.HasField('summary'):
            eventContext.event.message = eventContext.event.summary
        elif not eventContext.event.HasField(
                'summary') and eventContext.event.HasField('message'):
            eventContext.event.summary = eventContext.event.message[:255]

        missingFields = ','.join(ifilterfalse(eventContext.event.HasField, self.REQUIRED_EVENT_FIELDS))
        if missingFields:
            raise DropEvent('Required event fields %s not found' % missingFields,
                            eventContext.event)

        return eventContext

class EventIdentifierPluginException(ProcessingException):
    pass
class EventIdentifierPluginFailure(EventIdentifierPluginException):
    pass
class EventIdentifierPluginAbort(EventIdentifierPluginException):
    pass

class BaseEventIdentifierPlugin(object):
    def _resolveElement(self, evtProcessorManager, catalog, eventContext, type_id_field,
                        identifier_field, uuid_field):
        """
        Lookup an element by identifier or uuid and make sure both
        identifier and uuid are set.
        """
        actor = eventContext.event.actor
        if actor.HasField(type_id_field):
            if not (actor.HasField(identifier_field) and actor.HasField(uuid_field)):
                if actor.HasField(uuid_field):
                    uuid = getattr(actor, uuid_field, None)
                    element = evtProcessorManager.getElementByUuid(uuid)
                    if element:
                        eventContext.log.debug('Identified element %s by uuid %s',
                                               element, uuid)
                        setattr(actor, identifier_field, element.id)
                    else:
                        eventContext.log.warning('Could not find element by uuid %s'
                                                 , uuid)

                elif actor.HasField(identifier_field):
                    type_id = getattr(actor, type_id_field, None)
                    identifier = getattr(actor, identifier_field, None)
                    if type_id == DEVICE:
                        element_uuid = evtProcessorManager.findDeviceUuid(identifier,
                                                                    eventContext.eventProxy.ipAddress)
                    else:
                        element_uuid = evtProcessorManager.getElementUuidById(catalog,
                                                                        type_id,
                                                                        identifier)

                    if element_uuid:
                        eventContext.log.debug('Identified element %s by id %s',
                                               element_uuid, identifier)
                        setattr(actor, uuid_field, element_uuid)
                    else:
                        eventContext.log.debug(
                                'Could not find element type %s with id %s', type_id
                                , identifier)
            else:
                if log.isEnabledFor(logging.DEBUG):
                    type_id = getattr(actor, type_id_field, None)
                    identifier = getattr(actor, identifier_field, None)
                    uuid = getattr(actor, uuid_field, None)
                    eventContext.log.debug('Element %s already fully identified by %s/%s', type_id, identifier, uuid)

    def resolveIdentifiers(self, eventContext, evtProcessorManager):
        """
        Update eventContext in place, updating/resolving identifiers and respective uuid's
        """
        eventContext.log.debug('Identifying event (%s)', self.__class__.__name__)

        # Get element, most likely a Device
        self._resolveElement(
                evtProcessorManager,
                None,
                eventContext,
                EventField.Actor.ELEMENT_TYPE_ID,
                EventField.Actor.ELEMENT_IDENTIFIER,
                EventField.Actor.ELEMENT_UUID
                )

        # Get element, most likely a Component
        actor = eventContext.event.actor
        if actor.HasField(EventField.Actor.ELEMENT_UUID):
            parent = evtProcessorManager.getElementByUuid(actor.element_uuid)
        else:
            parent = None
        self._resolveElement(
                evtProcessorManager,
                parent,
                eventContext,
                EventField.Actor.ELEMENT_SUB_TYPE_ID,
                EventField.Actor.ELEMENT_SUB_IDENTIFIER,
                EventField.Actor.ELEMENT_SUB_UUID
                )

class IdentifierPipe(EventProcessorPipe):
    """
    Resolves element uuids and identifiers to make sure both are populated.
    """

    dependencies = [CheckInputPipe]

    def __call__(self, eventContext):
        eventContext.log.debug('Identifying event')

        # get list of defined IEventIdentifierPlugins (add default identifier to the end)
        evtIdentifierPlugins = [v for v in getUtilitiesFor(IEventIdentifierPlugin) if v[0] != 'default']
        evtIdentifierPlugins.append(('default', getUtility(IEventIdentifierPlugin, name="default")))

        # iterate over all event identifier plugins
        for name, plugin in evtIdentifierPlugins:
            try:
                eventContext.log.debug("running identifier plugin, name=%s, plugin=%s", name, plugin)
                plugin.resolveIdentifiers(eventContext, self._manager)
            except EventIdentifierPluginAbort as e:
                eventContext.log.debug(e)
                raise
            except EventIdentifierPluginException as e:
                eventContext.log.debug(e)

        return eventContext

class AddDeviceContextAndTagsPipe(EventProcessorPipe):
    """
    Adds device and component info to the context and event proxy.
    """
    dependencies = [IdentifierPipe]

    # use defined detail keys for consistent tag names
    DEVICE_DEVICECLASS_TAG_KEY = EventProxy.DEVICE_CLASS_DETAIL_KEY
    DEVICE_LOCATION_TAG_KEY = EventProxy.DEVICE_LOCATION_DETAIL_KEY
    DEVICE_SYSTEMS_TAG_KEY = EventProxy.DEVICE_SYSTEMS_DETAIL_KEY
    DEVICE_GROUPS_TAG_KEY = EventProxy.DEVICE_GROUPS_DETAIL_KEY
    COMPONENT_GROUP_TAG_KEY = EventProxy.COMPONENT_GROUP_DETAIL_KEY

    DEVICE_TAGGERS = {
        DEVICE_DEVICECLASS_TAG_KEY: (lambda device: device.deviceClass(), 'DeviceClass'),
        DEVICE_LOCATION_TAG_KEY    : (lambda device: device.location(), 'Location'),
        DEVICE_SYSTEMS_TAG_KEY     : (lambda device: device.systems(), 'Systems'),
        DEVICE_GROUPS_TAG_KEY      : (lambda device: device.groups(), 'DeviceGroups'),
    }

    COMPONENT_TAGGERS = {
        COMPONENT_GROUP_TAG_KEY: (lambda component: component.getComponentGroups(), 'ComponentGroups'),
    }

    def _addDeviceOrganizerNames(self, orgs, orgtypename, evtproxy, proxydetailkey, asDelimitedList=False):
        if orgtypename not in orgs:
            return

        orgnames = orgs[orgtypename]
        if orgnames:
            if asDelimitedList:
                detailOrgnames = orgnames
                proxyOrgname = '|' + '|'.join(orgnames)
            else:
                # just use 0'th  element
                detailOrgnames = orgnames[0]
                proxyOrgname = orgnames
            evtproxy.setReadOnly(orgtypename, proxyOrgname)
            evtproxy.details[proxydetailkey] = detailOrgnames

    def _addDeviceContext(self, eventContext, device):
        evtproxy = eventContext.eventProxy
        ipAddress = evtproxy.ipAddress or device.manageIp
        if ipAddress:
            evtproxy.ipAddress = ipAddress

        prodState = device.getProductionState()
        if prodState:
            evtproxy.prodState = prodState

        devicePriority = device.getPriority()
        if devicePriority:
            evtproxy.DevicePriority = devicePriority

    def _addDeviceOrganizers(self, eventContext, orgs):
        evtproxy = eventContext.eventProxy
        self._addDeviceOrganizerNames(orgs, 'Location', evtproxy, EventProxy.DEVICE_LOCATION_DETAIL_KEY)
        self._addDeviceOrganizerNames(orgs, 'DeviceClass', evtproxy, EventProxy.DEVICE_CLASS_DETAIL_KEY)
        self._addDeviceOrganizerNames(orgs, 'DeviceGroups', evtproxy, EventProxy.DEVICE_GROUPS_DETAIL_KEY, asDelimitedList=True)
        self._addDeviceOrganizerNames(orgs, 'Systems', evtproxy, EventProxy.DEVICE_SYSTEMS_DETAIL_KEY, asDelimitedList=True)

    def _addComponentOrganizers(self, eventContext, orgs):
        evtproxy = eventContext.eventProxy
        self._addDeviceOrganizerNames(orgs, 'ComponentGroups', evtproxy, EventProxy.COMPONENT_GROUP_DETAIL_KEY)

    def _findTypeIdAndElement(self, eventContext, sub_element):
        actor = eventContext.event.actor
        if sub_element:
            type_id_field = EventField.Actor.ELEMENT_SUB_TYPE_ID
            uuid_field = EventField.Actor.ELEMENT_SUB_UUID
        else:
            type_id_field = EventField.Actor.ELEMENT_TYPE_ID
            uuid_field = EventField.Actor.ELEMENT_UUID
        type_id = None
        element = None
        if actor.HasField(type_id_field):
            type_id = getattr(actor, type_id_field)
        if actor.HasField(uuid_field):
            element = self._manager.getElementByUuid(getattr(actor, uuid_field))
        return type_id, element

    def __call__(self, eventContext):
        actor = eventContext.event.actor

        # Set identifier and title based on resolved object
        element_type_id, element = self._findTypeIdAndElement(eventContext, False)
        if element:
            actor.element_identifier = element.id
            elementTitle = element.titleOrId()
            if elementTitle != actor.element_identifier:
                try:
                    actor.element_title = elementTitle
                except ValueError:
                    actor.element_title = elementTitle.decode('utf8')

        sub_element_type_id, sub_element = self._findTypeIdAndElement(eventContext, True)
        if sub_element:
            actor.element_sub_identifier = sub_element.id
            subElementTitle = sub_element.titleOrId()
            if subElementTitle != actor.element_sub_identifier:
                try:
                    actor.element_sub_title = subElementTitle
                except ValueError:
                    actor.element_sub_title = subElementTitle.decode('utf8')

        device = eventContext.deviceObject
        if device is None:
            if element_type_id == DEVICE:
                device = element
            elif sub_element_type_id == DEVICE:
                device = sub_element

            if device:
                eventContext.setDeviceObject(device)

                # find all organizers for this device, and add their uuids to
                # the appropriate event tags
                deviceOrgs = {}
                for tagType, orgProcessValues in self.DEVICE_TAGGERS.iteritems():
                    getOrgFunc,orgTypeName = orgProcessValues
                    objList = getOrgFunc(device)
                    if objList:
                        if not isinstance(objList, list):
                            objList = [objList]
                        uuids = set(sum((self._manager.getUuidsOfPath(obj) for obj in objList), []))
                        if uuids:
                            eventContext.eventProxy.tags.addAll(tagType, uuids)

                        # save this list of organizers names of this type, to add their names
                        # to the device event context
                        deviceOrgs[orgTypeName] = [obj.getOrganizerName() for obj in objList]

                self._addDeviceContext(eventContext, device)
                self._addDeviceOrganizers(eventContext, deviceOrgs)

        component = eventContext.componentObject
        if component is None:

            if element_type_id == COMPONENT:
                component = element
            elif sub_element_type_id == COMPONENT:
                component = sub_element

            if component:
                componentOrgs = {}
                eventContext.setComponentObject(component)
                for tagType, orgProcessValues in self.COMPONENT_TAGGERS.iteritems():
                    getOrgFunc, orgTypeName = orgProcessValues
                    objList = getOrgFunc(component)
                    if objList:
                        if not isinstance(objList, list):
                            objList = [objList]
                        uuids = set(sum((self._manager.getUuidsOfPath(obj) for obj in objList), []))
                        if uuids:
                            eventContext.eventProxy.tags.addAll(tagType, uuids)
                        componentOrgs[orgTypeName] = [obj.getOrganizerName() for obj in objList]
                self._addComponentOrganizers(eventContext, componentOrgs)

        return eventContext

class UpdateDeviceContextAndTagsPipe(AddDeviceContextAndTagsPipe):

    def __call__(self, eventContext):
        evtproxy = eventContext.eventProxy

        if eventContext.deviceObject is None:
            # Clear title fields
            actor = eventContext.event.actor
            actor.ClearField(EventField.Actor.ELEMENT_TITLE)
            actor.ClearField(EventField.Actor.ELEMENT_UUID)
            actor.ClearField(EventField.Actor.ELEMENT_SUB_TITLE)
            actor.ClearField(EventField.Actor.ELEMENT_SUB_UUID)
            eventContext.log.debug("device was cleared, must purge references in current event: %s", to_dict(eventContext._zepRawEvent))
            # clear out device-specific tags and details
            deviceOrganizerTypeNames = list(type for function,type in self.DEVICE_TAGGERS.values())
            deviceDetailNames = set(deviceOrganizerTypeNames +
                                    self.DEVICE_TAGGERS.keys() +
                                    [
                                        EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY,
                                        EventProxy.DEVICE_PRIORITY_DETAIL_KEY,
                                        EventProxy.PRODUCTION_STATE_DETAIL_KEY,
                                    ])

            # clear device context details
            for detail in deviceDetailNames:
                evtproxy.resetReadOnly(detail)
                if detail in evtproxy.details:
                    del evtproxy.details[detail]

            # clear device-dependent tags
            evtproxy.tags.clearType(self.DEVICE_TAGGERS.keys())
            eventContext.log.debug("reset device values in event before reidentifying: %s", to_dict(eventContext._zepRawEvent))

        return eventContext

class SerializeContextPipe(EventProcessorPipe):
    """
    Takes fields added to the eventProxy that couldn't directly be mapped out of the
    proxy and applies them to the event protobuf.
    """
    dependencies = [AddDeviceContextAndTagsPipe]

    def __call__(self, eventContext):
        eventContext.log.debug('Saving context back to event')
        return eventContext

class AssignDefaultEventClassAndTagPipe(EventProcessorPipe):
    """
    If the event class has not yet been set by the time this pipe is reached, set
    it to a default value.
    """
    def __call__(self, eventContext):
        eventClassName = eventContext.eventProxy.eventClass
        # Set event class to Unknown if not specified
        if not eventClassName:
            eventContext.eventProxy.eventClass = eventClassName = ZenEventClasses.Unknown

        # Define tags for this event class
        eventClass = self._manager.getEventClassOrganizer(eventClassName)
        if eventClass and not eventContext.eventProxy.tags.getByType(TransformPipe.EVENT_CLASS_TAG):
            try:
                eventClassUuids = self._manager.getUuidsOfPath(eventClass)
                if eventClassUuids:
                    eventContext.eventProxy.tags.addAll(TransformPipe.EVENT_CLASS_TAG, eventClassUuids)
            except (KeyError, AttributeError):
                log.info("Event has nonexistent event class %s.", eventClass)

        if eventClass:
            self._setEventFlappingSettings(eventContext, eventClass)
        return eventContext

    def _setEventFlappingSettings(self, eventContext, eventClass):
        """
        Add the event flappings settings from the event class zproperties.
        This might be better as a separate pipe.
        """
        # the migrate script might not have ran yet so make sure the properties exist
        if getattr(eventClass, 'zFlappingIntervalSeconds', None):
            eventContext.eventProxy.flappingInterval = eventClass.zFlappingIntervalSeconds
            eventContext.eventProxy.flappingThreshold = eventClass.zFlappingThreshold
            eventContext.eventProxy.flappingSeverity = eventClass.zFlappingSeverity


class FingerprintPipe(EventProcessorPipe):
    """
    Calculates event's fingerprint/dedupid.
    """

    DEFAULT_FINGERPRINT_FIELDS = (
    'device', 'component', 'eventClass', 'eventKey', 'severity')
    NO_EVENT_KEY_FINGERPRINT_FIELDS = (
    'device', 'component', 'eventClass', 'severity', 'summary')

    dependencies = [AddDeviceContextAndTagsPipe]

    def __call__(self, eventContext):
        event = eventContext.event

        if event.HasField(EventField.FINGERPRINT):
            fp = event.fingerprint
            eventContext.eventProxy.dedupid = fp
            eventContext.log.debug("incoming event has a preset fingerprint %s", fp)
        else:
            dedupFields = self.DEFAULT_FINGERPRINT_FIELDS
            if not (event.HasField(EventField.EVENT_KEY) and
                    getattr(event, EventField.EVENT_KEY, None)):
                dedupFields = self.NO_EVENT_KEY_FINGERPRINT_FIELDS

            dedupIdList = [str(getattr(eventContext.eventProxy, field, '')) for
                           field in dedupFields]

            eventContext.eventProxy.dedupid = '|'.join(dedupIdList)

            eventContext.log.debug('Created dedupid of %s from %s',
                                   eventContext.eventProxy.dedupid, dedupIdList)

        return eventContext

class TransformAndReidentPipe(EventProcessorPipe):
    dependencies = [AddDeviceContextAndTagsPipe]

    def __init__(self, manager, transformpipe, reidentpipes):
        super(TransformAndReidentPipe, self).__init__(manager)
        self.transformPipe = transformpipe
        self.reidentpipes = reidentpipes

    def __call__(self, eventContext):
        # save original values of device and component, to see if they get modified in the transform
        original_device = eventContext.eventProxy.device
        original_component = eventContext.eventProxy.component

        # perform transform
        eventContext = self.transformPipe(eventContext)

        # see if we need to rerun indent/context pipes
        if (eventContext.eventProxy.device != original_device or
            eventContext.eventProxy.component != original_component):

            # clear object references if device/components change
            if eventContext.eventProxy.device != original_device:
                eventContext.setDeviceObject(None)
                eventContext.setComponentObject(None)

            if eventContext.eventProxy.component != original_component:
                eventContext.setComponentObject(None)

            original_prodState = eventContext.eventProxy.prodState

            # rerun any pipes necessary to reidentify event
            for pipe in self.reidentpipes:
                eventContext = pipe(eventContext)

            if not eventContext.eventProxy.prodState and original_prodState:
                eventContext.eventProxy.prodState = original_prodState

        return eventContext

class TransformPipe(EventProcessorPipe):

    EVENT_CLASS_TAG = 'zenoss.event.event_class'

    ACTION_HISTORY = 'history'
    ACTION_DROP = 'drop'
    ACTION_STATUS = 'status'
    ACTION_HEARTBEAT = 'heartbeat'
    ACTION_LOG = 'log'
    ACTION_ALERT_STATE = 'alert_state'
    ACTION_DETAIL = 'detail'

    ACTION_STATUS_MAP = {
        ACTION_HISTORY: STATUS_CLOSED,
        ACTION_STATUS: STATUS_NEW,
        ACTION_DROP: STATUS_DROPPED,
    }

    def _tagEventClasses(self, eventContext, eventClass):
        """
        Adds a set of tags for the hierarchy of event classes for this event
        NOTE: We must tag the event classes at this part of the pipeline
        before a mapping has been applied otherwise the mapping instance
        won't be tagged, just the Event Class that was mapped.
        """
        try:
            eventClassUuids = self._manager.getUuidsOfPath(eventClass)
            if eventClassUuids:
                eventContext.eventProxy.tags.addAll(self.EVENT_CLASS_TAG, eventClassUuids)
        except (KeyError, AttributeError):
            log.info("Event has nonexistent event class %s.", eventClass)

    def __call__(self, eventContext):
        eventContext.log.debug('Mapping and Transforming event')
        evtclass = self._manager.lookupEventClass(eventContext)
        transform_enabled = evtclass.transformEnabled
        if transform_enabled:
            apply_transforms = getattr(eventContext.event, 'apply_transforms', True)
            if not apply_transforms:
                eventContext.log.debug('Not applying transforms, regexes or zProperties because apply_transforms'
                                       ' was false')
        else:
            eventContext.log.debug('Not applying transforms, transformEnabled is set to False.')
            apply_transforms = False
        if evtclass:
            self._tagEventClasses(eventContext, evtclass)

            if apply_transforms:
                evtclass.applyExtraction(eventContext.eventProxy)
                evtclass.applyValues(eventContext.eventProxy)
            if eventContext.eventProxy.eventClassMapping:
                eventContext.event.event_class_mapping_uuid = IGlobalIdentifier(evtclass).getGUID()
            if apply_transforms:
                evtclass.applyTransform(eventContext.eventProxy,
                                        eventContext.deviceObject,
                                        eventContext.componentObject)
        return eventContext

class EventPluginPipe(EventProcessorPipe):
    def __init__(self, manager, pluginInterface, name=''):
        super(EventPluginPipe, self).__init__(manager, name)

        self._eventPlugins = tuple(getUtilitiesFor(pluginInterface))

    def __call__(self, eventContext):
        for name, plugin in self._eventPlugins:
            try:
                plugin.apply(eventContext._eventProxy, self._manager.dmd)
            except Exception as e:
                eventContext.log.error(
                        'Event plugin %s encountered an error -- skipping.', name)
                eventContext.log.exception(e)
                continue

        return eventContext

class ClearClassRefreshPipe(EventProcessorPipe):
    def __call__(self, eventContext):
        eventContext.refreshClearClasses()
        return eventContext

class TestPipeExceptionPipe(EventProcessorPipe):
    # pipe used for testing exception handling in event processor
    def __init__(self, exceptionClass=ProcessingException):
        self.exceptionClass = exceptionClass

    def __call__(self, eventContext):
        raise self.exceptionClass('Testing pipe processing failure')

class CheckHeartBeatPipe(EventProcessorPipe):
    """
    After the mappings and transforms have been applied, we
    need to recheck to see if it is a HeartBeat event as those are
    treated differently.
    """
    def __call__(self, eventContext):
        proxy = eventContext.eventProxy
        if proxy.eventClass == ZenEventClasses.Heartbeat:
            log.debug("Converting %s to a heartbeat event", proxy)
            # do not publish this event
            proxy._action = proxy.ACTION_DROP
            try:
                self._manager.dmd.ZenEventManager._sendHeartbeat(proxy)
            except Exception as e:
                log.error("Unable to send heartbeat event %s", proxy)
                log.exception(e)
        return eventContext
