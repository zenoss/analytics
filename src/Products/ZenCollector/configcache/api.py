##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import logging
import time

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .cache import DeviceQuery
from .dispatcher import DeviceConfigTaskDispatcher, OidMapTaskDispatcher
from .handlers import (
    NewDeviceHandler,
    DeviceUpdateHandler,
    MissingConfigsHandler,
)
from .utils import DeviceProperties, getDeviceConfigServices, OidMapProperties

log = logging.getLogger("zen.configcache")


class ConfigCache(object):
    """
    Implements an API for manipulating the Configuration Cache to the rest
    of the system.
    """

    @classmethod
    def new(cls):
        client = getRedisClient(url=getRedisUrl())
        devicestore = createObject("deviceconfigcache-store", client)
        configClasses = getDeviceConfigServices()
        devicedispatcher = DeviceConfigTaskDispatcher(configClasses)
        oidmapstore = createObject("oidmapcache-store", client)
        oidmapdispatcher = OidMapTaskDispatcher()
        return cls(
            devicestore, devicedispatcher, oidmapstore, oidmapdispatcher
        )

    def __init__(self, devstore, devdispatch, oidstore, oiddispatch):
        self.__new = NewDeviceHandler(log, devstore, devdispatch)
        self.__update = DeviceUpdateHandler(log, devstore, devdispatch)
        self.__missing = MissingConfigsHandler(log, devstore, devdispatch)
        self.__stores = type(
            "Store",
            (object,),
            {
                "device": devstore,
                "oidmap": oidstore,
            }
        )()
        self.__oidmapdispatcher = oiddispatch

    def update_device(self, device):
        """
        Expires or retires existing configs for the device and sends build
        jobs to speculatively create new configurations for the device.
        May also delete configurations if a job produces no config for
        configuration that existed previously.
        """
        monitor = device.getPerformanceServerName()
        if monitor is None:
            raise RuntimeError(
                "Device '%s' is not a member of a collector" % (device.id,)
            )
        props = DeviceProperties(device)
        buildlimit = props.build_timeout
        # Check for device class change
        stored_uid = self.__stores.device.get_uid(device.id)
        if device.getPrimaryPath() != stored_uid:
            self.__new(device.id, monitor, buildlimit, False)
        else:
            # Note: the store's `search` method only returns keys for configs
            # that exist.
            keys_with_config = tuple(
                self.__stores.device.search(
                    DeviceQuery(monitor=monitor, device=device.id)
                )
            )
            minttl = props.minimum_ttl
            self.__update(keys_with_config, minttl)
            self.__missing(device.id, monitor, keys_with_config, buildlimit)

    def update_oidmaps(self):
        """
        Expires the cached oidmap data.
        """
        timeout = OidMapProperties().build_timeout
        self.__oidmapdispatcher.dispatch(timeout, time.time())
