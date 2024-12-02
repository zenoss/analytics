##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import time

from .cache import DeviceKey, DeviceQuery, ConfigStatus


class NewDeviceHandler(object):
    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self.dispatcher = dispatcher

    def __call__(self, deviceId, monitor, buildlimit, newDevice=True):
        all_keys = {
            DeviceKey(svcname, monitor, deviceId)
            for svcname in self.dispatcher.service_names
        }
        query = DeviceQuery(device=deviceId, monitor=monitor)
        pending_keys = {
            status.key
            for status in self.store.query_statuses(query)
            if isinstance(status, ConfigStatus.Pending)
        }
        non_pending_keys = all_keys - pending_keys
        for key in pending_keys:
            self.log.info(
                "build job already submitted for this config  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
        now = time.time()
        self.store.set_pending(*((key, now) for key in non_pending_keys))
        for key in non_pending_keys:
            self.dispatcher.dispatch(
                key.service, key.monitor, key.device, buildlimit, now
            )
            self.log.info(
                "submitted build job for %s  "
                "device=%s collector=%s service=%s",
                "new device" if newDevice else "device with new device class",
                key.device,
                key.monitor,
                key.service,
            )


class DeviceUpdateHandler(object):
    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self.dispatcher = dispatcher

    def __call__(self, keys, minttl):
        statuses = tuple(
            status
            for status in (self.store.get_status(key) for key in keys)
            if not isinstance(
                status,
                (
                    # These statuses won't get 'stuck' in a wait period
                    # before manager handles them.
                    ConfigStatus.Expired,
                    ConfigStatus.Retired,
                ),
            )
        )

        now = time.time()
        retirement = now - minttl

        # Transitioning to Retired is relevant only for Current.
        retired = {
            status.key
            for status in statuses
            if isinstance(status, ConfigStatus.Current)
            and status.updated >= retirement
        }
        expired = {
            status.key for status in statuses if status.key not in retired
        }

        self.store.set_retired(*((key, now) for key in retired))
        self.store.set_expired(*((key, now) for key in expired))

        for key in retired:
            self.log.info(
                "retired configuration of changed device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
        for key in expired:
            self.log.info(
                "expired configuration of changed device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )


class MissingConfigsHandler(object):
    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self.dispatcher = dispatcher

    def __call__(self, deviceId, monitor, keys, buildlimit):
        """
        @param keys: These keys are associated with a config
        @type keys: Sequence[DeviceKey]
        """
        # Send a job for for all config services that don't currently have
        # an associated configuration.  Some ZenPacks, i.e. vSphere, defer
        # their modeling to a later time, so jobs for configuration services
        # must be sent to pick up any new configs.
        hasconfigs = tuple(key.service for key in keys)
        noconfigkeys = tuple(
            DeviceKey(svcname, monitor, deviceId)
            for svcname in self.dispatcher.service_names
            if svcname not in hasconfigs
        )
        # Identify all no-config keys that already have a status.
        skipkeys = tuple(
            key
            for key in noconfigkeys
            if self.store.get_status(key) is not None
        )
        now = time.time()
        for key in (k for k in noconfigkeys if k not in skipkeys):
            self.store.set_pending((key, now))
            self.dispatcher.dispatch(
                key.service, key.monitor, key.device, buildlimit, now
            )
            self.log.debug(
                "submitted build job for possibly missing config  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )


class RemoveConfigsHandler(object):
    def __init__(self, log, store):
        self.log = log
        self.store = store

    def __call__(self, keys):
        self.store.remove(*keys)
        for key in keys:
            self.log.info(
                "removed configuration of deleted device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
