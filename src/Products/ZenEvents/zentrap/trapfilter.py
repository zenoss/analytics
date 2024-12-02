##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from twisted.internet import defer
from zope.interface import implementer

from Products.ZenHub.interfaces import (
    ICollectorEventTransformer,
    TRANSFORM_CONTINUE,
    TRANSFORM_DROP,
)

from .filterspec import countOidLevels

log = logging.getLogger("zen.zentrap.trapfilter")


@implementer(ICollectorEventTransformer)
class TrapFilter(object):
    """
    Interface used to perform filtering of events at the collector.
    This could be used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated
    for the event, so they can set fields which are used by an
    ICollectorEventFingerprintGenerator.

    The priority of the event transformer (the transformers are executed in
    ascending order using the weight of each filter).
    """

    # implements ICollectorEventTransformer
    weight = 1

    def __init__(self, app, spec):
        self._app = app
        self._filterspec = spec
        self._checksum = None
        self._filters = (
            GenericV1Predicate(self._filterspec.v1traps),
            EnterpriseV1Predicate(self._filterspec.v1filters),
            SnmpV2Predicate(self._filterspec.v2filters),
        )

    # implements ICollectorEventTransformer
    def transform(self, event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be
            forwarded on to the next transformer in the sequence,
            TRANSFORM_STOP if no further transformers should be performed on
            this event, and TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
        result = TRANSFORM_CONTINUE
        snmpVersion = event.get("snmpVersion", None)
        if snmpVersion and self._filterspec.defined:
            log.debug("filtering V%s event %s", snmpVersion, event)
            if self._dropEvent(event):
                log.debug("dropping event %s", event)
                self._app.counters["eventFilterDroppedCount"] += 1
                result = TRANSFORM_DROP
        else:
            log.debug(
                "filter skipped  snmp-version=%s filters-defined=%s event=%s",
                snmpVersion,
                self._filterspec.defined,
                event,
            )
        return result

    @defer.inlineCallbacks
    def task(self):
        log.debug("retrieving trap filters")
        try:
            service = yield self._app.getRemoteConfigServiceProxy()
            checksum, trapfilters = yield service.callRemote(
                "getTrapFilters", self._checksum
            )
            if checksum is None:
                log.debug("no update on trap filters")
                defer.returnValue(None)

            trapfilters = trapfilters if trapfilters is not None else ""
            events = self._filterspec.update_from_string(trapfilters)
            for event in events:
                mesg = event.get("message")
                if mesg:
                    log.warn(mesg)
                self._app.sendEvent(event)

            state = "updated" if self._checksum is not None else "initial"
            log.info("applied %s trap filters", state)
            self._checksum = checksum
        except Exception:
            log.exception("failed to retrieve trap filters")

    def _dropEvent(self, event):
        """
        Determine if an event should be dropped.
        Assumes there are some filters defined, so the default if no matching
        filter is found should be True; i.e. the event did not match any
        existing filter that would include it, so therefore we should drop it.

        @param event: The event to drop or keep.
        @return: Returns True if the event should be dropped;
            False if the event be kept.
        @rtype: boolean
        """
        trapfilter = next(
            (tf for tf in self._filters if tf.is_valid(event)), None
        )
        if trapfilter:
            log.debug("using trap filter %r", trapfilter)
            return trapfilter(event)
        log.error("dropping unknown trap  event=%r", event)
        return True


class TrapFilterPredicate(object):
    """
    Base class for predicates that determine whether a trap is ignored.

    Predicate implementations will return True indicating that the
    event should be ignored.
    """

    def __init__(self, definitions):
        self._definitions = definitions

    def is_valid(self, event):
        return False

    def __call__(self, event):
        return False


class GenericV1Predicate(TrapFilterPredicate):
    def __init__(self, *args):
        super(GenericV1Predicate, self).__init__(*args)
        self._genericTraps = frozenset([0, 1, 2, 3, 4, 5])

    def is_valid(self, event):
        if event.get("snmpVersion", None) != "1":
            return False
        if event.get("snmpV1GenericTrapType", None) not in self._genericTraps:
            return False
        return True

    def __call__(self, event):
        traptype = event.get("snmpV1GenericTrapType", None)
        definition = self._definitions.get(traptype, None)
        if definition and not definition.exclude:
            return False
        return True


class EnterpriseV1Predicate(TrapFilterPredicate):
    def is_valid(self, event):
        if event.get("snmpVersion", None) != "1":
            return False
        if event.get("snmpV1GenericTrapType", None) != 6:
            return False
        return True

    def __call__(self, event):
        oid = event.get("snmpV1Enterprise", None)
        if oid is None:
            log.error(
                "No OID found for enterprise-specific trap for V1 event: %s",
                event,
            )
            return True

        return _check_definitions(
            (
                getter()
                for getter in (
                    # order is important!
                    lambda: self._getSpecificTrapDefinition(event, oid),
                    lambda: self._getWildCardDefinition(oid),
                    lambda: self._getGlobMatchDefinition(oid),
                )
            )
        )

    def _getSpecificTrapDefinition(self, event, enterpriseOID):
        specificTrap = event.get("snmpV1SpecificTrap", None)
        if specificTrap is None:
            return None
        key = "".join([enterpriseOID, "-", str(specificTrap)])
        definition = _findFilterByLevel(key, self._definitions)
        if definition:
            log.debug("matched [specific-trap] definition %s", definition)
        return definition

    def _getWildCardDefinition(self, enterpriseOID):
        key = "".join([enterpriseOID, "-", "*"])
        definition = _findFilterByLevel(key, self._definitions)
        if definition:
            log.debug("matched [wildcard] definition %s", definition)
        return definition

    def _getGlobMatchDefinition(self, enterpriseOID):
        definition = _findClosestGlobbedFilter(
            enterpriseOID, self._definitions
        )
        if definition:
            log.debug("matched [glob] definition %s", definition)
        return definition


class SnmpV2Predicate(TrapFilterPredicate):
    def is_valid(self, event):
        return event.get("snmpVersion", None) in ("2", "3")

    def __call__(self, event):
        oid = event["oid"]
        return _check_definitions(
            (
                getter()
                for getter in (
                    # order is important!
                    lambda: self._getExactMatchDefinition(oid),
                    lambda: self._getGlobMatchDefinition(oid),
                )
            )
        )

    def _getExactMatchDefinition(self, oid):
        # First, try an exact match on the OID
        definition = _findFilterByLevel(oid, self._definitions)
        if definition:
            log.debug("matched [exact] definition %s", definition)
        return definition

    def _getGlobMatchDefinition(self, oid):
        definition = _findClosestGlobbedFilter(oid, self._definitions)
        if definition:
            log.debug("matched [glob] definition %s", definition)
        return definition


def _check_definitions(definitions):
    definition = next((defn for defn in definitions if defn is not None), None)
    if definition is None:
        log.debug("no matching definitions found")
        return True
    return definition.exclude


def _findClosestGlobbedFilter(oid, filtersByLevel):
    filterDefinition = None
    globbedValue = oid
    while globbedValue != "*":
        globbedValue = getNextHigherGlobbedOid(globbedValue)
        filterDefinition = _findFilterByLevel(globbedValue, filtersByLevel)
        if filterDefinition:
            break
    return filterDefinition


def _findFilterByLevel(oid, filtersByLevel):
    filterDefinition = None
    oidLevels = countOidLevels(oid)
    filtersByOid = filtersByLevel.get(oidLevels, None)
    if filtersByOid is not None and len(filtersByOid) > 0:
        filterDefinition = filtersByOid.get(oid, None)
    return filterDefinition


def getNextHigherGlobbedOid(oid):
    """
    Gets the next highest globbed OID based on OID hierarchy.
    For instance, given an oid of or "1.2.3.4" or 1.2.3.4.*", return "1.2.3.*".

    @return: The next highest globbed OID up to just "*"
    @rtype: string
    """
    dotIndex = oid.rfind(".")
    if dotIndex != -1 and oid[dotIndex:] == ".*":
        dotIndex = oid.rfind(".", 0, dotIndex)

    if dotIndex < 1 or dotIndex == len(oid) - 1:
        nextGlobbedOID = "*"
    else:
        nextGlobbedOID = "".join([oid[0:dotIndex], ".*"])
    return nextGlobbedOID
