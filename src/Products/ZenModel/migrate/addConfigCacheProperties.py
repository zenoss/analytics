##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from Products.ZenCollector.configcache.constants import Constants
from Products.ZenRelations.zPropertyCategory import setzPropertyCategory

from . import Migrate


_properties = (
    (
        (
            Constants.device_time_to_live_id,
            Constants.device_time_to_live_value,
        ),
        {
            "type": "int",
            "label": "Device configuration expiration",
            "description": (
                "The maximum number of seconds to wait before rebuilding a "
                "device configuration."
            ),
        },
    ),
    (
        (
            Constants.device_minimum_time_to_live_id,
            Constants.device_minimum_time_to_live_value,
        ),
        {
            "type": "int",
            "label": "Device configuration pre-expiration window",
            "description": (
                "The number of seconds the configuration is protected "
                "from being rebuilt."
            ),
        },
    ),
    (
        (
            Constants.device_build_timeout_id,
            Constants.device_build_timeout_value,
        ),
        {
            "type": "int",
            "label": "Device configuration build timeout",
            "description": (
                "The number of seconds allowed for building a device "
                "configuration."
            ),
        },
    ),
    (
        (
            Constants.device_pending_timeout_id,
            Constants.device_pending_timeout_value,
        ),
        {
            "type": "int",
            "label": "Device configuration build queued timeout",
            "description": (
                "The number of seconds a device configuration build may be "
                "queued before a timeout."
            ),
        },
    ),
)


class addConfigCacheProperties(Migrate.Step):
    """
    Add the zDeviceConfigTTL, zDeviceConfigBuildTimeout, and
    zDeviceConfigPendingTimeout z-properties to /Devices.
    """

    version = Migrate.Version(200, 7, 0)

    def cutover(self, dmd):
        for args, kwargs in _properties:
            if not dmd.Devices.hasProperty(args[0]):
                dmd.Devices._setProperty(*args, **kwargs)
            setzPropertyCategory(args[0], "Config Cache")


addConfigCacheProperties()
