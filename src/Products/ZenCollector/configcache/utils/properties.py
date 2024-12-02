##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

from ..constants import Constants


class OidMapProperties(object):
    def __init__(self):
        self._conf = getGlobalConfiguration()

    @property
    def ttl(self):
        return self._conf.getint(
            Constants.oidmap_time_to_live_id,
            Constants.oidmap_time_to_live_value,
        )

    @property
    def pending_timeout(self):
        return self._conf.getint(
            Constants.oidmap_pending_timeout_id,
            Constants.oidmap_pending_timeout_value,
        )

    @property
    def build_timeout(self):
        return self._conf.getint(
            Constants.oidmap_build_timeout_id,
            Constants.oidmap_build_timeout_value,
        )


class DeviceProperties(object):
    def __init__(self, device):
        self._device = device

    @property
    def ttl(self):
        return _getZProperty(
            self._device,
            Constants.device_time_to_live_id,
            Constants.device_time_to_live_value,
        )

    @property
    def minimum_ttl(self):
        return _getZProperty(
            self._device,
            Constants.device_minimum_time_to_live_id,
            Constants.device_minimum_time_to_live_value,
        )

    @property
    def pending_timeout(self):
        return _getZProperty(
            self._device,
            Constants.device_pending_timeout_id,
            Constants.device_pending_timeout_value,
        )

    @property
    def build_timeout(self):
        return _getZProperty(
            self._device,
            Constants.device_build_timeout_id,
            Constants.device_build_timeout_value,
        )


def _getZProperty(obj, propname, default):
    value = obj.getZ(propname)
    if value is None:
        return default
    return value
