##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

from cStringIO import StringIO
from hashlib import sha256

from Acquisition import aq_base
from zope.interface import implementer

from Products.ZenHub.interfaces import (
    FILTER_CONTINUE,
    FILTER_EXCLUDE,
    FILTER_INCLUDE,
    IInvalidationFilter,
)
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.ZenModel.GraphPoint import GraphPoint
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.Monitor import Monitor
from Products.ZenModel.MibModule import MibModule
from Products.ZenModel.MibNode import MibNode
from Products.ZenModel.MibNotification import MibNotification
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.ZenModel.ProductClass import ProductClass
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.Software import Software
from Products.ZenWidgets.Portlet import Portlet
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from ..constants import Constants

log = logging.getLogger("zen.{}".format(__name__.split(".")[-1].lower()))


@implementer(IInvalidationFilter)
class IgnorableClassesFilter(object):
    """Ignore invalidations on certain classes."""

    CLASSES_TO_IGNORE = (
        IpAddress,
        IpNetwork,
        GraphDefinition,
        GraphPoint,
        Monitor,
        Portlet,
        ProductClass,
        ServiceClass,
        Software,
    )

    def initialize(self, context):
        pass

    def include(self, obj):
        if isinstance(obj, self.CLASSES_TO_IGNORE):
            log.debug("IgnorableClassesFilter is ignoring %s ", obj)
            return FILTER_EXCLUDE
        return FILTER_CONTINUE


_iszorcustprop = re.compile("[zc][A-Z]").match

_excluded_properties = (
    Constants.device_build_timeout_id,
    Constants.device_pending_timeout_id,
    Constants.device_time_to_live_id,
    Constants.device_minimum_time_to_live_id,
)


def _include_property(propId):
    if propId in _excluded_properties:
        return None
    return _iszorcustprop(propId)


def _getZorCProperties(organizer):
    for zId in sorted(organizer.zenPropertyIds(pfilt=_include_property)):
        try:
            if organizer.zenPropIsPassword(zId):
                propertyString = organizer.getProperty(zId, "")
            else:
                propertyString = organizer.zenPropertyString(zId)
            yield zId, propertyString
        except AttributeError:
            # ZEN-3666: If an attribute error is raised on a zProperty
            # assume it was produced by a zenpack
            # install whose daemons haven't been restarted and continue
            # excluding the offending property.
            log.debug("Excluding '%s' property", zId)


@implementer(IInvalidationFilter)
class BaseOrganizerFilter(object):
    """
    Base invalidation filter for organizers.

    The default implementation will reject organizers that do not have
    updated calculated checksum values. The checksum is calculated using
    accumulation of each 'z' and 'c' property associated with organizer.
    """

    weight = 10

    def __init__(self, types):
        self._types = types

    def getRoot(self, context):
        return context.dmd.primaryAq()

    def initialize(self, context):
        root = self.getRoot(context)
        brains = IModelCatalogTool(root).search(self._types)
        results = {}
        for brain in brains:
            try:
                obj = brain.getObject()
                results[brain.getPath()] = self.organizerChecksum(obj)
            except KeyError:
                log.warn("Unable to retrieve object: %s", brain.getPath())
        self.checksum_map = results

    def organizerChecksum(self, organizer):
        m = sha256()
        self.generateChecksum(organizer, m)
        return m.hexdigest()

    def generateChecksum(self, organizer, hash_checksum):
        # Checksum all zProperties and custom properties
        for zId, propertyString in _getZorCProperties(organizer):
            hash_checksum.update("%s|%s" % (zId, propertyString))

    def include(self, obj):
        # Move on if it's not one of our types
        if not isinstance(obj, self._types):
            return FILTER_CONTINUE

        # Checksum the device class
        current_checksum = self.organizerChecksum(obj)
        organizer_path = "/".join(obj.getPrimaryPath())

        # Get what we have right now and compare
        existing_checksum = self.checksum_map.get(organizer_path)
        if current_checksum != existing_checksum:
            log.debug("%r has a new checksum! Including.", obj)
            self.checksum_map[organizer_path] = current_checksum
            return FILTER_CONTINUE
        log.debug("%r checksum unchanged. Skipping.", obj)
        return FILTER_EXCLUDE


class DeviceClassInvalidationFilter(BaseOrganizerFilter):
    """
    Invalidation filter for DeviceClass organizers.

    Uses both 'z' and 'c' properties as well as locally bound RRD templates
    to create the checksum.
    """

    def __init__(self):
        super(DeviceClassInvalidationFilter, self).__init__((DeviceClass,))

    def getRoot(self, context):
        return context.dmd.Devices.primaryAq()

    def generateChecksum(self, organizer, hash_checksum):
        """
        Generate a checksum representing the state of the device class as it
        pertains to configuration. This takes into account templates and
        zProperties, nothing more.
        """
        s = StringIO()
        # Checksum includes all bound templates
        for tpl in organizer.rrdTemplates():
            s.seek(0)
            s.truncate()
            try:
                tpl.exportXml(s)
            except Exception:
                log.exception(
                    "unable to export XML of template  template=%r", tpl
                )
            else:
                hash_checksum.update(s.getvalue())
        # Include z/c properties from base class
        super(DeviceClassInvalidationFilter, self).generateChecksum(
            organizer, hash_checksum
        )


class OSProcessOrganizerFilter(BaseOrganizerFilter):
    """Invalidation filter for OSProcessOrganizer objects."""

    def __init__(self):
        super(OSProcessOrganizerFilter, self).__init__((OSProcessOrganizer,))

    def getRoot(self, context):
        return context.dmd.Processes.primaryAq()


class OSProcessClassFilter(BaseOrganizerFilter):
    """
    Invalidation filter for OSProcessClass objects.

    This filter uses 'z' and 'c' properties as well as local _properties
    defined on the organizer to create a checksum.
    """

    def __init__(self):
        super(OSProcessClassFilter, self).__init__((OSProcessClass,))

    def getRoot(self, context):
        return context.dmd.Processes.primaryAq()

    def generateChecksum(self, organizer, hash_checksum):
        # Include properties of OSProcessClass
        for prop in organizer._properties:
            prop_id = prop["id"]
            hash_checksum.update(
                "%s|%s" % (prop_id, getattr(organizer, prop_id, ""))
            )
        # Include z/c properties from base class
        super(OSProcessClassFilter, self).generateChecksum(
            organizer, hash_checksum
        )


@implementer(IInvalidationFilter)
class MibFilter(object):
    """
    Invalidation filter for MibModule objects.

    This filter uses 'z' and 'c' properties as well as local _properties
    defined on the organizer to create a checksum.
    """

    def initialize(self, context):
        pass

    def include(self, obj):
        if not isinstance(
            obj, (MibOrganizer, MibModule, MibNode, MibNotification)
        ):
            return FILTER_CONTINUE
        # log.info(
        #     "Detected a MIB invalidation  type=%s id=%s",
        #     type(aq_base(obj)).__name__,
        #     obj.id,
        # )
        return FILTER_INCLUDE
