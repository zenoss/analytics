##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from itertools import chain
from logging import getLogger

from zope.component.factory import Factory
from zope.interface import implements

from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.Zing import fact as ZFact
from Products.Zing.interfaces import IZingObjectUpdateHandler
from Products.Zing.tx_state import ZingTxStateManager


log = getLogger("zen.zing.model_updates")


class ZingObjectUpdateHandler(object):
    implements(IZingObjectUpdateHandler)

    def __init__(self, context):
        self.context = context.getDmd()
        self.zing_tx_state_manager = ZingTxStateManager()

    def is_object_relevant(self, obj):
        # devices and components with an uuid are relevant
        uuid = None
        try:
            uuid = obj.getUUID()
        except Exception:
            pass
        return uuid and (
            isinstance(obj, Device) or
            isinstance(obj, DeviceComponent) or
            isinstance(obj, DeviceOrganizer))

    def _get_zing_tx_state(self):
        """ """
        return self.zing_tx_state_manager.get_zing_tx_state(self.context)

    def _update_object(self, obj, idxs=None):
        if not self.is_object_relevant(obj):
            return

        tx_state = self._get_zing_tx_state()
        uuid = obj.getUUID()
        tx_state.need_deletion_fact.pop(uuid, None)
        log.debug("buffering object update for {}".format(uuid))

        if isinstance(obj, DeviceOrganizer):
            fact = ZFact.device_organizer_info_fact(obj)
            tx_state.need_device_organizer_info_fact[uuid] = fact

        elif isinstance(obj, Device):
            parent = obj.getPrimaryParent().getPrimaryParent()

            device_fact = ZFact.device_info_fact(obj)
            device_fact.metadata[ZFact.DimensionKeys.PARENT_KEY] = parent.getUUID()
            device_fact.metadata[ZFact.DimensionKeys.RELATION_KEY] = obj.getPrimaryParent().id
            device_fact.metadata[ZFact.MetadataKeys.ZEN_SCHEMA_TAGS_KEY] = "Device"
            tx_state.need_device_info_fact[uuid] = device_fact

            device_org_fact = ZFact.organizer_fact_from_device(obj)
            tx_state.need_organizers_fact[uuid] = device_org_fact

        elif isinstance(obj, DeviceComponent):
            parent = obj.getPrimaryParent().getPrimaryParent()
            if parent.id in ('os', 'hw'):
                parent = parent.device()

            comp_fact = ZFact.device_info_fact(obj)
            comp_fact.metadata[ZFact.DimensionKeys.PARENT_KEY] = parent.getUUID()
            comp_fact.metadata[ZFact.DimensionKeys.RELATION_KEY] = obj.getPrimaryParent().id
            comp_fact.metadata[ZFact.MetadataKeys.ZEN_SCHEMA_TAGS_KEY] = "DeviceComponent"
            tx_state.need_device_info_fact[uuid] = comp_fact

            device_org_fact = ZFact.organizer_fact_from_device(obj.device())
            comp_org_fact = ZFact.organizer_fact_from_device_component(
                device_org_fact, uuid, obj.meta_type, obj.getComponentGroupNames)
            tx_state.need_organizers_fact[uuid] = comp_org_fact

    def _delete_object(self, obj):
        if self.is_object_relevant(obj):
            uuid = obj.getUUID()
            log.debug("buffering object deletion for {}".format(uuid))
            tx_state = self._get_zing_tx_state()
            tx_state.need_deletion_fact[uuid] = ZFact.deletion_fact(uuid)

    def update_object(self, obj, idxs=None):
        """
        ModelCatalog calls this method when an object needs to be updated
        """
        try:
            self._update_object(obj, idxs)
        except Exception:
            log.exception("Exception buffering object update for Zing")

    def delete_object(self, obj):
        """
        ModelCatalog calls this method when an object needs to be deleted
        """
        try:
            self._delete_object(obj)
        except Exception:
            log.exception("Exception buffering object deletion for Zing")

    def _generate_facts(self, uuid_to_fact, already_generated=None, tx_state=None):
        """
        :param uuid_to_fact: dict uuid: Fact
        :param already_generated: uuids for which we have already generated a fact
        :return: Fact generator
        """
        for uuid, fact in uuid_to_fact.iteritems():
            if already_generated and uuid in already_generated:
                continue
            if fact.is_valid():
                if already_generated:
                    already_generated.add(uuid)
                if tx_state is not None:
                    impact_fact = ZFact.impact_relationships_fact_if_needed(tx_state, uuid)
                    if impact_fact:
                        yield impact_fact
                yield fact

    def generate_facts(self, tx_state):
        """
        @return: Fact generator
        """
        fact_generators = []
        if tx_state.need_device_info_fact:
            # TODO set this to debug
            log.info("Processing {} device info updates".format(len(tx_state.need_device_info_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_device_info_fact,
                                   tx_state.already_generated_device_info_facts, tx_state))
        if tx_state.need_device_organizer_info_fact:
            # TODO set this to debug
            log.info("Processing {} device organizer info updates".format(len(tx_state.need_device_organizer_info_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_device_organizer_info_fact,
                                   tx_state.already_generated_device_organizer_info_facts))
        if tx_state.need_organizers_fact:
            # TODO set this to debug
            log.info("Processing {} organizers updates".format(len(tx_state.need_organizers_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_organizers_fact,
                                   tx_state.already_generated_organizer_facts))
        if tx_state.need_deletion_fact:
            # TODO set this to debug
            log.info("Processing {} deletion updates".format(len(tx_state.need_deletion_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_deletion_fact))
        return chain(*fact_generators)


OBJECT_UPDATE_HANDLER_FACTORY = Factory(ZingObjectUpdateHandler)

