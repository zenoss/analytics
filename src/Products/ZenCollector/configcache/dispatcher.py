##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from .tasks import build_device_config, build_oidmap


class DeviceConfigTaskDispatcher(object):
    """Encapsulates the act of dispatching the build_device_config task."""

    def __init__(self, configClasses):
        """
        Initialize a DeviceConfigTaskDispatcher instance.

        The `configClasses` parameter should be the classes used to create
        the device configurations.

        @type configClasses: Sequence[Class]
        """
        self._classnames = {
            cls.__module__: ".".join((cls.__module__, cls.__name__))
            for cls in configClasses
        }

    @property
    def service_names(self):
        return self._classnames.keys()

    def dispatch_all(self, monitorid, deviceid, timeout, submitted):
        """
        Submit a task to build a device configuration from each
        configuration service.
        """
        soft_limit, hard_limit = _get_limits(timeout)
        for name in self._classnames.values():
            build_device_config.apply_async(
                args=(monitorid, deviceid, name),
                kwargs={"submitted": submitted},
                soft_time_limit=soft_limit,
                time_limit=hard_limit,
            )

    def dispatch(self, servicename, monitorid, deviceid, timeout, submitted):
        """
        Submit a task to build device configurations for the specified device.

        @type servicename: str
        @type monitorid: str
        @type deviceId: str
        """
        name = self._classnames.get(servicename)
        if name is None:
            raise ValueError("service name '%s' not found" % servicename)
        soft_limit, hard_limit = _get_limits(timeout)
        build_device_config.apply_async(
            args=(monitorid, deviceid, name),
            kwargs={"submitted": submitted},
            soft_time_limit=soft_limit,
            time_limit=hard_limit,
        )


class OidMapTaskDispatcher(object):
    """Encapsulates the act of dispatching the build_oidmap_config task."""

    def dispatch(self, timeout, submitted):
        soft_limit, hard_limit = _get_limits(timeout)
        build_oidmap.apply_async(
            kwargs={"submitted": submitted},
            soft_time_limit=soft_limit,
            time_limit=hard_limit,
        )


def _get_limits(timeout):
    return timeout, (timeout + (timeout * 0.1))
