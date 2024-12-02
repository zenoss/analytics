##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from itertools import chain

from ZODB.POSException import POSKeyError
from zope.component import subscribers

from Products.ZenHub.interfaces import (
    FILTER_INCLUDE,
    FILTER_EXCLUDE,
    IInvalidationOid,
)
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)

from .invalidation import Invalidation, InvalidationCause
from .pipeline import Pipe, IterablePipe, Action
from .utils import into_tuple

log = logging.getLogger("zen.configcache.modelchange")


class InvalidationProcessor(object):
    """Takes an invalidation and produces ZODB objects.

    An invalidation is represented as an ZODB object ID (oid).
    An oid is accepted by the `get` method and a sequence of ZODB objects
    are returned.  Generally, only one object is in the sequence, but it
    is possible for more than one object to be returned.
    """

    def __init__(self, app, filters):
        """Initialize an InvalidationProcessor instance.

        :param app: The dmd object
        :type app:
        :param filters: A list of filters to apply to the invalidation
        :type filters:
        """
        oid2obj_1 = Pipe(OidToObject(app))
        oid2obj_2 = IterablePipe(OidToObject(app))
        apply_filter = Pipe(ApplyFilters(filters))
        apply_transforms = Pipe(ApplyTransforms())

        self.__results = CollectInvalidations()
        collect = Pipe(self.__results)

        oid2obj_1.connect(apply_filter)
        oid2obj_1.connect(collect, tid=OidToObject.SINK)
        apply_filter.connect(apply_transforms)
        apply_transforms.connect(oid2obj_2)
        apply_transforms.connect(collect, tid=ApplyTransforms.SINK)
        oid2obj_2.connect(collect)
        oid2obj_2.connect(collect, tid=OidToObject.SINK)

        self.__pipeline = oid2obj_1.node()

    def apply(self, oid):
        """Send data into the pipeline."""
        self.__pipeline.send(oid)
        return self.__results.pop()


class OidToObject(Action):
    """Validates the OID to ensure it references a device."""

    SINK = "sink1"

    def __init__(self, app):
        """
        Initialize an OidToObject instance.

        :param app: ZODB application root object.
        :type app: OFS.Application.Application
        """
        super(OidToObject, self).__init__()
        self._app = app

    def __call__(self, oid):
        try:
            # Retrieve the object using its OID.
            obj = self._app._p_jar[oid]
        except POSKeyError:
            # Skip if this OID doesn't exist.
            return
        # Exclude the object if it doesn't have the right base class.
        if not isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
            return
        try:
            # Wrap the bare object into an Acquisition wrapper.
            obj = obj.__of__(self._app.zport.dmd).primaryAq()
        except (AttributeError, KeyError):
            # An exception at this implies a deleted device.
            return (
                self.SINK,
                Invalidation(oid, obj, InvalidationCause.Removed),
            )
        else:
            return (
                self.DEFAULT,
                Invalidation(oid, obj, InvalidationCause.Updated),
            )


class ApplyFilters(Action):
    """
    Filter the invalidation against IInvalidationFilter objects.

    Invalidations explicitely excluded by a filter are dropped from the
    pipeline.
    """

    def __init__(self, filters):
        """
        Initialize a FilterObject instance.

        :param filters: The invalidation filters.
        :type filters: Sequence[IInvalidationFilter]
        """
        super(ApplyFilters, self).__init__()
        self._filters = filters

    def __call__(self, invalidation):
        for fltr in self._filters:
            result = fltr.include(invalidation.entity)
            if result in (FILTER_INCLUDE, FILTER_EXCLUDE):
                if result is FILTER_EXCLUDE:
                    log.debug(
                        "invalidation excluded by filter  filter=%r entity=%s",
                        fltr,
                        invalidation.entity,
                    )
                break
        else:
            result = FILTER_INCLUDE
        if result is not FILTER_EXCLUDE:
            return invalidation


class ApplyTransforms(Action):
    """
    The invalidation pipeline concerns itself with certain types of
    objects.  The `ApplyTransforms` node determines whether the OID refers
    to a nested object within a desired object type and if the OID is
    a nested object, the OID of the parent object is returned to be used
    in its place.
    """

    SINK = "sink2"

    def __call__(self, invalidation):
        # First, get any subscription adapters registered as transforms
        adapters = subscribers((invalidation.entity,), IInvalidationOid)
        # Next check for an old-style (regular adapter) transform
        try:
            adapters = chain(
                adapters, (IInvalidationOid(invalidation.entity),)
            )
        except TypeError:
            # No old-style adapter is registered
            pass
        transformed = set()
        for adapter_ in adapters:
            result = adapter_.transformOid(invalidation.oid)
            if isinstance(result, str):
                transformed.add(result)
            elif hasattr(result, "__iter__"):
                # If the transform didn't give back a string, it should have
                # given back an iterable
                transformed.update(result)
            else:
                log.warn(
                    "IInvalidationOid adaptor returned a bad result  "
                    "adaptor=%r result=%r entity=%s oid=%s",
                    adapter_,
                    result,
                    invalidation.entity,
                    invalidation.oid,
                )
        # Remove any Nones a transform may have returned.
        transformed.discard(None)
        # Remove the original OID from the set of transformed OIDs;
        # we don't want the original OID if any OIDs were returned.
        transformed.discard(invalidation.oid)

        if transformed:
            return (self.DEFAULT, transformed)
        return (self.SINK, (invalidation,))


class CollectInvalidations(Action):
    """Collects the results of the pipeline."""

    def __init__(self):
        self._output = set()

    def __call__(self, result):
        results = into_tuple(result)
        entities = []
        for result in results:
            entities.append(result)
            log.debug(
                "collected an invalidation  reason=%s entity=%s oid=%r",
                result.reason,
                result.entity,
                result.oid,
            )
        self._output.update(entities)

    def pop(self):
        """Return the collected data, removing it from the set."""
        try:
            return self._output.copy()
        finally:
            self._output.clear()
