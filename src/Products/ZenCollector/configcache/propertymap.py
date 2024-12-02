##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from .constants import Constants

log = logging.getLogger("zen.configcache.propertymap")


class DevicePropertyMap(object):
    """
    This class accepts a mapping of ZODB paths to a value.

    Users can interrogate the class instance by providing a path and
    expecting the value from the mapping that best matches the given path.

    A 'best match' means the path with the longest match starting from the
    left end of the path.
    """

    @classmethod
    def make_ttl_map(cls, obj):
        return cls(
            getPropertyValues(
                obj,
                Constants.device_time_to_live_id,
                Constants.device_time_to_live_value,
                _getZProperty,
            ),
            Constants.device_time_to_live_value,
        )

    @classmethod
    def make_minimum_ttl_map(cls, obj):
        return cls(
            getPropertyValues(
                obj,
                Constants.device_minimum_time_to_live_id,
                Constants.device_minimum_time_to_live_value,
                _getZProperty,
            ),
            Constants.device_minimum_time_to_live_value,
        )

    @classmethod
    def make_pending_timeout_map(cls, obj):
        return cls(
            getPropertyValues(
                obj,
                Constants.device_pending_timeout_id,
                Constants.device_pending_timeout_value,
                _getZProperty,
            ),
            Constants.device_pending_timeout_value,
        )

    @classmethod
    def make_build_timeout_map(cls, obj):
        return cls(
            getPropertyValues(
                obj,
                Constants.device_build_timeout_id,
                Constants.device_build_timeout_value,
                _getZProperty,
            ),
            Constants.device_build_timeout_value,
        )

    def __init__(self, values, default):
        self.__values = tuple(
            (p.split("/")[1:], v) for p, v in values.items() if v is not None
        )
        self.__default = default

    def smallest_value(self):
        try:
            return min(self.__values, key=lambda item: item[1])[1]
        except ValueError as ex:
            # Check whether the ValueError is about an empty sequence.
            # If it's not, re-raise the exception.
            if "arg is an empty sequence" not in str(ex):
                raise
            return self.__default

    def get(self, request_uid):
        # Be graceful on accepted input values.  None is equivalent
        # to no match so return the default value.
        if request_uid is None:
            return self.__default
        # Split the request into its parts
        req_parts = request_uid.split("/")[1:]
        # Find all the path parts that match the request
        matches = (
            (len(parts), value)
            for parts, value in self.__values
            if req_parts[0 : len(parts)] == parts
        )
        try:
            # Return the value associated with the path parts having
            # the longest match with the request.
            return max(matches, key=lambda item: item[0])[1]
        except ValueError as ex:
            # Check whether the ValueError is about an empty sequence.
            # If it's not, re-raise the exception.
            if "arg is an empty sequence" not in str(ex):
                raise
            # No path parts matched the request.
            return self.__default


def getPropertyValues(obj, propname, default, getter, relName="devices"):
    """
    Returns a mapping of UID -> property-value for the given z-property.
    """
    values = {obj.getPrimaryId(): getter(obj, propname, default)}
    values.update(
        (inst.getPrimaryId(), getter(inst, propname, default))
        for inst in obj.getSubInstances(relName)
        if inst.isLocal(propname)
    )
    values.update(
        (inst.getPrimaryId(), getter(inst, propname, default))
        for inst in obj.getOverriddenObjects(propname)
    )
    if not values or any(v is None for v in values.values()):
        raise RuntimeError(
            "one or more values are None or z-property is missing  "
            "z-property=%s" % (propname,)
        )
    return values


def _getZProperty(obj, propname, default):
    value = obj.getZ(propname)
    if value is None:
        return default
    return value
