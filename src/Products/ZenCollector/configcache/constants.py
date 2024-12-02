##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class Constants(object):

    device_build_timeout_id = "zDeviceConfigBuildTimeout"
    device_pending_timeout_id = "zDeviceConfigPendingTimeout"
    device_time_to_live_id = "zDeviceConfigTTL"
    device_minimum_time_to_live_id = "zDeviceConfigMinimumTTL"

    # Default values
    device_build_timeout_value = 7200
    device_pending_timeout_value = 7200
    device_time_to_live_value = 43200
    device_minimum_time_to_live_value = 0

    oidmap_build_timeout_id = "configcache-oidmap-build-timeout"
    oidmap_pending_timeout_id = "configcache-oidmap-pending-timeout"
    oidmap_time_to_live_id = "configcache-oidmap-ttl"

    # Default values
    oidmap_build_timeout_value = 7200
    oidmap_pending_timeout_value = 7200
    oidmap_time_to_live_value = 43200
