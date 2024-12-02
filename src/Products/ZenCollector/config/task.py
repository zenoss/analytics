##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import time

from twisted.internet import defer

log = logging.getLogger("zen.collector.config")


class ConfigurationLoaderTask(object):
    """
    Periodically retrieves collector configuration via the
    IConfigurationProxy service.
    """

    # Deprecated attribute kept because zenvsphere uses it for reasons
    # that are no longer relevant.
    STATE_FETCH_DEVICE_CONFIG = "n/a"

    def __init__(self, collector, proxy):
        self._collector = collector
        self._proxy = proxy

    @defer.inlineCallbacks
    def __call__(self):
        try:
            properties = yield self._proxy.getPropertyItems()
            self._processPropertyItems(properties)

            thresholdClasses = yield self._proxy.getThresholdClasses()
            self._processThresholdClasses(thresholdClasses)

            thresholds = yield self._proxy.getThresholds()
            self._processThresholds(thresholds)

            yield self._collector.runPostConfigTasks()
        except Exception:
            log.exception(
                "failed to retrieve collector configuration  "
                "collection-daemon=%s",
                self._collector.name,
            )

    def _processPropertyItems(self, propertyItems):
        log.debug("processing received property items")
        if propertyItems:
            self._collector._setCollectorPreferences(propertyItems)

    def _processThresholdClasses(self, thresholdClasses):
        log.debug("processing received threshold classes")
        if thresholdClasses:
            self._collector.loadThresholdClasses(thresholdClasses)

    def _processThresholds(self, thresholds):
        log.debug("processing received thresholds")
        if thresholds:
            self._collector._configureThresholds(thresholds)


class SingleDeviceConfigLoader(object):
    """Handles retrieving the config of a single device."""

    def __init__(self, deviceid, collector, service, options, callback):
        self._deviceId = deviceid
        self._collector = collector
        self._service = service
        self._options = options
        self._callback = callback

    @property
    def deviceIds(self):
        return [self._deviceId]

    @defer.inlineCallbacks
    def __call__(self):
        try:
            ref = yield self._collector.getRemoteConfigCacheProxy()

            log.debug("fetching device config for %s", self._deviceId)
            # get options from prefs.options and send to remote
            config = yield ref.callRemote(
                "getDeviceConfig",
                self._service,
                self._deviceId,
                options=self._options.__dict__,
            )
            yield self._callback(config)
        except Exception:
            log.exception("failed to retrieve device configs")


class ManyDeviceConfigLoader(object):
    """Handles retrieving devices from the ConfigCache service."""

    def __init__(self, proxy, callback):
        self._proxy = proxy
        self._callback = callback
        self._deviceIds = set()
        self._changes_since = 0

    @property
    def deviceIds(self):
        return self._deviceIds

    @defer.inlineCallbacks
    def __call__(self):
        log.debug("fetching device configs")
        try:
            next_time = time.time()
            config_data = yield self._proxy.getConfigProxies(
                self._changes_since, self._deviceIds
            )
            yield self._processConfigs(config_data)
            self._changes_since = next_time
        except Exception:
            log.exception("failed to retrieve device configs")

    @defer.inlineCallbacks
    def _processConfigs(self, config_data):
        new = config_data.get("new", ())
        updated = config_data.get("updated", ())
        removed = config_data.get("removed", ())
        try:
            try:
                yield self._callback(new, updated, removed)
            finally:
                self._update_local_cache(new, updated, removed)
        except Exception:
            log.exception("failed to process device configs")

    def _update_local_cache(self, new, updated, removed):
        self._deviceIds.difference_update(removed)
        self._deviceIds.update(cfg.id for cfg in new)
