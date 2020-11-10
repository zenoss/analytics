##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018-2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import copy
import logging
import time

from json import JSONEncoder

from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError

from Products.ZenModel.ComponentGroup import ComponentGroup
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.Location import Location

from .interfaces import IImpactRelationshipsFactProvider
from .shortid import shortid

log = logging.getLogger("zen.zing.fact")

ORGANIZERS_FACT_PLUGIN = "zen_organizers"
DEVICE_INFO_FACT_PLUGIN = "zen_device_info"
DEVICE_ORGANIZER_INFO_FACT_PLUGIN = "zen_device_organizer_info"
COMPONENT_GROUP_INFO_FACT_PLUGIN = "zen_component_group_info"
DELETION_FACT_PLUGIN = "zen_deletion"
DYNAMIC_SERVICE_FACT_PLUGIN = "zen_impact_dynamic_service"


class DimensionKeys(object):
    CONTEXT_UUID_KEY = "contextUUID"
    META_TYPE_KEY = "meta_type"
    PLUGIN_KEY = "plugin"
    PARENT_KEY = "parent"
    RELATION_KEY = "relationship"


class MetadataKeys(object):
    NAME_KEY = "name"
    MEM_CAPACITY_KEY = "mem_capacity"
    LOCATION_KEY = "location"
    DEVICE_CLASS_KEY = "device_class"
    GROUPS_KEY = "groups"
    SYSTEMS_KEY = "systems"
    PROD_STATE_KEY = "prod_state"
    DELETED_KEY = "_zen_deleted_entity"
    COMPONENT_GROUPS_KEY = "component_groups"
    IMPACT_DS_ORG_KEY = "impact_ds_organizer"
    IMPACT_DS_IMPACTERS_KEY = "dynamic_service_impacters"
    ZEN_SCHEMA_TAGS_KEY = "zen_schema_tags"
    ID_KEY = "id"
    TITLE_KEY = "title"
    DEVICE_UUID_KEY = "device_uuid"
    DEVICE_KEY = "device"


class Fact(object):
    def __init__(self, f_id=None):
        if not f_id:
            f_id = shortid()
        self.id = f_id
        self.metadata = {}  # corresponds to "dimensions" in zing
        self.data = {}  # corresponds to "metadata" in zing

    def __str__(self):
        return "ZING.fact {}   metadata: {!r}  data: {!r}".format(
            self.id, self.metadata, self.data
        )

    def update(self, other):
        self.data.update(other)

    def is_valid(self):
        return self.metadata.get(DimensionKeys.CONTEXT_UUID_KEY) is not None

    def set_context_uuid_from_object(self, obj):
        self.metadata[DimensionKeys.CONTEXT_UUID_KEY] = get_context_uuid(obj)

    def set_meta_type_from_object(self, obj):
        self.metadata[DimensionKeys.META_TYPE_KEY] = obj.meta_type


def get_context_uuid(obj):
    uuid = ""
    try:
        uuid = obj.getUUID()
    except Exception:
        pass
    return uuid


def deletion_fact(obj_uuid):
    f = Fact()
    f.metadata.update({
        DimensionKeys.CONTEXT_UUID_KEY: obj_uuid,
        DimensionKeys.PLUGIN_KEY: DELETION_FACT_PLUGIN,
    })
    f.data.update({
        MetadataKeys.DELETED_KEY: True,
    })
    return f


def device_organizer_info_fact(device_organizer):
    """
    Given a DeviceOrganizer, generates its fact
    """
    f = Fact()
    f.set_context_uuid_from_object(device_organizer)
    f.set_meta_type_from_object(device_organizer)
    f.metadata[DimensionKeys.PLUGIN_KEY] = DEVICE_ORGANIZER_INFO_FACT_PLUGIN
    f.data[MetadataKeys.NAME_KEY] = device_organizer.getOrganizerName()

    # Ignore root DeviceOrganizer (/) and DataRoot as parents.
    parent = device_organizer.getPrimaryParent()
    if (
        isinstance(parent, DeviceOrganizer)
        and parent.getOrganizerName() != "/"
    ):
        f.metadata[DimensionKeys.PARENT_KEY] = parent.getUUID()

    if device_organizer.aqBaseHasAttr("description"):
        f.data["description"] = device_organizer.description

    if isinstance(device_organizer, Location):
        if device_organizer.address:
            f.data["z.map.address"] = device_organizer.address

        if device_organizer.latlong:
            f.data["z.map.latlong"] = device_organizer.latlong

    return f


def component_group_info_fact(component_group):
    f = Fact()
    f.set_context_uuid_from_object(component_group)
    f.set_meta_type_from_object(component_group)
    f.metadata[DimensionKeys.PLUGIN_KEY] = COMPONENT_GROUP_INFO_FACT_PLUGIN
    f.data[MetadataKeys.NAME_KEY] = component_group.getOrganizerName()

    # Ignore root ComponentGroup (/) and DataRoot as parents.
    parent = component_group.getPrimaryParent()
    if isinstance(parent, ComponentGroup) and parent.getOrganizerName() != "/":
        f.metadata[DimensionKeys.PARENT_KEY] = parent.getUUID()

    if component_group.aqBaseHasAttr("description"):
        f.data["description"] = component_group.description

    return f


def device_info_fact(device):
    """
    Given a device or component, generates its device info fact
    """
    f = Fact()
    f.set_context_uuid_from_object(device)
    f.set_meta_type_from_object(device)
    f.metadata[DimensionKeys.PLUGIN_KEY] = DEVICE_INFO_FACT_PLUGIN
    f.data[MetadataKeys.NAME_KEY] = device.titleOrId()
    f.data[MetadataKeys.PROD_STATE_KEY] = device.getProductionStateString()
    for propdict in device._propertyMap():
        propId = propdict.get("id")
        if device.isLocal(propId) and propdict.get("type", None) in (
            "string",
            "int",
            "boolean",
            "long",
            "float",
            "text",
            "lines",
        ):
            # Some of the device properties can be methods,
            # so we have to call them and get values.
            if callable(device.getProperty(propId)):
                log.warn("Callable: %s", device.getProperty(propId))
                try:
                    value = device.getProperty(propId).__call__()
                except TypeError as e:
                    log.exception(
                        "Unable to call property: %s. Exception %s",
                        device.getProperty(propId),
                        e,
                    )
            else:
                value = device.getProperty(propId)
            if value is None:
                value = ""
            f.data[propId] = value
    f.data[MetadataKeys.ID_KEY] = device.id
    f.data[MetadataKeys.TITLE_KEY] = device.title
    try:
        f.data.update({
            MetadataKeys.DEVICE_UUID_KEY: get_context_uuid(device.device()),
            MetadataKeys.DEVICE_KEY: device.device().id,
        })
    except Exception:
        pass
    return f


def organizer_fact_from_device(device):
    """
    Given a device, generates its organizers fact
    """
    device_fact = Fact()
    device_fact.set_context_uuid_from_object(device)
    device_fact.set_meta_type_from_object(device)
    device_fact.metadata[DimensionKeys.PLUGIN_KEY] = ORGANIZERS_FACT_PLUGIN
    location = device.getLocationName()
    device_fact.data.update({
        MetadataKeys.DEVICE_CLASS_KEY: device.getDeviceClassName(),
        MetadataKeys.LOCATION_KEY: [location] if location else [],
        MetadataKeys.SYSTEMS_KEY: device.getSystemNames(),
        MetadataKeys.GROUPS_KEY: device.getDeviceGroupNames(),
    })
    return device_fact


def organizer_fact_from_device_component(
    device_fact, comp_uuid, comp_meta_type, comp_groups
):
    """
    Given a device component, generates its organizers fact
    @param device_fact: organizers fact for device
    """
    comp_fact = copy.deepcopy(device_fact)
    comp_fact.metadata[DimensionKeys.CONTEXT_UUID_KEY] = comp_uuid
    comp_fact.metadata[DimensionKeys.META_TYPE_KEY] = comp_meta_type
    comp_fact.data[MetadataKeys.COMPONENT_GROUPS_KEY] = comp_groups
    comp_fact.id = shortid()
    return comp_fact

def organizer_fact_without_groups_from_device_component(
    device_fact, comp_uuid, comp_meta_type
):
    """
    Given a device component, generates its organizers fact.  This is identical
    to organizer_fact_from_device_component, except that it doesn't
    set COMPONENT_GROUPS_KEY in the resulting fact.   (Omitting it is different
    than setting it to an empty value!)   It may be used in situations where
    the device organizers are being changed and we only need to update the
    organizers that came from device_fact.
    @param device_fact: organizers fact for device
    """
    comp_fact = copy.deepcopy(device_fact)
    comp_fact.metadata[DimensionKeys.CONTEXT_UUID_KEY] = comp_uuid
    comp_fact.metadata[DimensionKeys.META_TYPE_KEY] = comp_meta_type
    comp_fact.id = shortid()
    return comp_fact

def impact_relationships_fact(uuid):
    try:
        fact_provider = getUtility(IImpactRelationshipsFactProvider)
    except ComponentLookupError:
        pass
    else:
        return fact_provider.impact_relationships_fact(uuid)
    return None


def impact_relationships_fact_if_needed(
    tx_state, uuid, mark_as_generated=True
):
    """
    Generates an impact relationships fact for the received uuid if it has
    not already been generated.

    Returns a valid impact realtionship fact or None if the object does not
    belong to impact graph, if the generated fact is not valid, or if the
    fact has already been generated.
    """
    impact_fact = None
    if (
        tx_state
        and tx_state.impact_installed
        and uuid not in tx_state.already_generated_impact_facts
    ):
        fact = impact_relationships_fact(uuid)
        mark = False
        if fact is None:
            mark = True  # this object doesnt belong to impact graph
        elif fact.is_valid():
            mark = True
            impact_fact = fact
        if mark_as_generated and mark:
            tx_state.already_generated_impact_facts.add(uuid)
    return impact_fact


class _FactEncoder(JSONEncoder):
    def _tweak_data(self, data_in):
        data_out = {}
        for k, v in data_in.iteritems():
            if (
                isinstance(v, list)
                or isinstance(v, tuple)
                or isinstance(v, set)
            ):
                # whatever comes in the list, set etc. needs to be scalar,
                # if it isn't cast it to string for now.
                # TODO: Review if we need to support more complex types
                # (list of lists, etc)
                values = []
                for x in v:
                    if not isinstance(x, (str, int, long, float, bool)):
                        log.debug(
                            "Found non scalar type in list (%s). "
                            "Casting it to str", x.__class__,
                        )
                        x = str(x)
                    values.append(x)
                data_out[k] = sorted(values)
            else:
                data_out[k] = [v]
        return data_out

    def default(self, o):
        if isinstance(o, Fact):
            return {
                "id": o.id,
                "data": self._tweak_data(o.data),
                "metadata": o.metadata,
                "timestamp": int(time.time()),
            }
        return JSONEncoder.default(self, o)


FactEncoder = _FactEncoder()


def _serialize(fact):
    try:
        return FactEncoder.encode(fact), True
    except Exception as ex:
        log.warn(
            "Skipping unserializable fact  error=%s fact=%s", ex, fact,
        )
        return None, False


def serialize_facts(facts):
    serialized_facts = []
    for fact in facts:
        data, successful = _serialize(fact)
        if successful:
            serialized_facts.append(data)
    if serialize_facts:
        return "{{\"models\": [{}]}}".format(", ".join(serialized_facts))
