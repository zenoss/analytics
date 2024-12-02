##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
IApplication* control-plane implementations.
"""

import logging
import re
import time

from collections import Sequence, Iterator
from fnmatch import fnmatch
from functools import wraps
from zope.interface import implementer

import six

from Products.ZenUtils.application import (
    IApplication,
    IApplicationConfiguration,
    IApplicationLog,
    IApplicationManager,
)
from Products.ZenUtils.controlplane import getConnectionSettings

from .client import ControlPlaneClient, ControlCenterError
from .environment import configuration as cc_config
from .runstates import RunStates

LOG = logging.getLogger("zen.controlplane")

MEM_MULTIPLIER = {
    "k": 1024,
    "m": 1024 * 1024,
    "g": 1024 * 1024 * 1024,
    "t": 1024 * 1024 * 1024 * 1024,
}


def getTenantId():
    """Returns the tenant ID from the environment."""
    tid = cc_config.tenant_id
    if not tid:
        LOG.error(
            "ERROR: Could not determine the tenantID from the environment"
        )
        return None
    return tid


def _search(services, params):
    """
    Returns a generator which produces ServiceDefinition objects.
    """
    if "name" in params:
        namepat = params["name"]
        services = (svc for svc in services if fnmatch(svc.name, namepat))
    if "tags" in params:
        tags = set(params["tags"])
        includes = set(t for t in tags if not t.startswith("-"))
        excludes = set(t[1:] for t in tags if t.startswith("-"))
        if includes:
            services = (
                svc
                for svc in services
                if svc.tags and (set(svc.tags) & includes == includes)
            )
        if excludes:
            services = (
                svc
                for svc in services
                if not svc.tags or excludes.isdisjoint(set(svc.tags))
            )
    return services


# NOTE: This cache is per-Zope instance only.
# Unfortunately, ControlCenter does _not_ identify deleted services
# via the 'since' API (the 'getChangesSince' method call on the client).
# This means that one Zope will have removed the deleted service(s) from
# its cache, but the other Zopes won't pick up this change until the TTL
# has expired on their caches and have the services reloaded.  The result
# is that deleted services may appear and disappear from the service listing
# if the browser client switches Zope instances during the TTL window.
#
# TODO: Update the ControlCenter REST API to support identification of
# removed services and/or implement this cache using redis or memcached (or
# something else equivalent) and have it shared among all the Zopes.


class _Cache(object):
    """Cache for ServiceDefinition objects."""

    def __init__(self, client, ttl=60):
        """Initialize an instance of _Cache.

        :param client: reference to the ControlCenterClient object.
        :param ttl: Number of seconds the cache may age before cleared.
        """
        self._client = client
        self._data = None
        self._lastUpdate = 0
        self._ttl = ttl

    def _load(self):
        """Load all the data into the cache."""
        tenant_id = getTenantId()
        if tenant_id is None:
            self._data = None
            self._lastUpdate = 0
        else:
            self._data = self._client.queryServices(tenantID=tenant_id)
            self._lastUpdate = time.time()

    def _refresh(self):
        """Update the cache with changes."""
        since = int((time.time() - self._lastUpdate) * 1000)
        # No refresh if no time has elapsed since the last update
        if since == 0:
            return
        changes = self._client.getChangesSince(since)
        if changes:
            # Changes exist, so refresh the last update time.
            self._lastUpdate = time.time()
        for changed_svc in changes:
            idx = next(
                (
                    idx
                    for idx, svc in enumerate(self._data)
                    if svc.id == changed_svc.id
                ),
                None,
            )
            if idx is not None:
                # Update existing service in cache
                self._data[idx] = changed_svc
            else:
                # Add the new service to the cache
                self._data.append(changed_svc)

    def get(self):
        """Return the cached data."""
        if not self.__nonzero__():
            self._load()
        else:
            self._refresh()
        return self._data

    def clear(self):
        """Clear the cache."""
        self._data = None
        self._lastUpdate = 0

    def __nonzero__(self):
        """Return True if there is cached data."""
        age = int(time.time() - self._lastUpdate)
        return age < self._ttl and self._data is not None


@implementer(IApplicationManager)
class DeployedAppLookup(object):
    """
    Query the control-plane for Zenoss application services.
    """

    # The class of the Control Plane client
    clientClass = ControlPlaneClient

    @staticmethod
    def _applicationClass():
        return DeployedApp

    def __init__(self):
        settings = getConnectionSettings()
        self._client = self.clientClass(**settings)
        # Cache RunState objects in order to persist state between requests
        #  to support RESTARTING state.
        self._statecache = {}
        self._servicecache = _Cache(self._client)

    def query(self, name=None, tags=None, monitorName=None):
        """
        Returns a sequence of IApplication objects.
        """
        services = self._servicecache.get()
        if not services:
            return ()

        params = {}
        if name:
            params["name"] = name
        if tags:
            if isinstance(tags, six.string_types):
                tags = [tags]
            params["tags"] = tags

        result = _search(services, params)

        # If monitorName is specified, filter for services which are
        # parented by the specified monitor.
        if monitorName:
            # Replace "daemon" with "-daemon" to exclude services which are
            # applications.
            tags = set(tags) - set(["daemon"])
            tags.add("-daemon")
            params = {"name": monitorName, "tags": list(tags)}
            parent = next(_search(services, params), None)
            # If the monitor name wasn't found, return an empty sequence.
            if not parent:
                return ()
            result = (svc for svc in result if svc.parentId == parent.id)

        return tuple(self._getApp(service) for service in result)

    def get(self, id, default=None):
        """
        Retrieve the IApplication object of the identified application.
        The default argument is returned if the application doesn't exist.
        """
        service = next(
            (svc for svc in self._servicecache.get() if svc.id == id), None
        )
        if not service:
            return default
        return self._getApp(service)

    def _getApp(self, service):
        runstate = self._statecache.get(service.id)
        if not runstate:
            runstate = RunStates()
            self._statecache[service.id] = runstate
        return self._applicationClass()(service, self._client, runstate)


@implementer(IApplication)
class DeployedApp(object):
    """
    Control and interact with the deployed app via the control plane.
    """

    UNKNOWN_STATUS = type(
        "SENTINEL", (object,), {"__nonzero__": lambda x: False}
    )()

    def __init__(self, service, client, runstate):
        self._client = client
        self._runstate = runstate
        self._service = service
        self._status = DeployedApp.UNKNOWN_STATUS

    def _initStatus(fn):
        """
        Decorator which calls updateStatus if status is uninitialized
        """

        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self._status == DeployedApp.UNKNOWN_STATUS:
                self.updateStatus(*args, **kwargs)
            return fn(self)

        return wrapper

    def updateStatus(self):
        """
        Retrieves the current running instance of the application.
        """
        try:
            result = self._client.queryServiceStatus(self._service.id)
            self._status = next(
                (i for i in result.itervalues() if i.instanceId == 0), None
            )
        except ControlCenterError as ex:
            if "No such entity" not in str(ex):
                LOG.error(ex)
            self._status = None  # No status on error
        if self._status is None:
            self._runstate.lost()
        else:
            self._runstate.found(self._status)

    @property
    def id(self):
        return self._service.id

    @property
    def name(self):
        return self._service.name

    @property
    @_initStatus
    def hostId(self):
        return self._status.hostId if self._status else None

    @property
    def description(self):
        return self._service.description

    @description.setter
    def description(self, desc):
        self._service.description = desc
        self._client.updateServiceProperty(self._service, "Description")

    @property
    @_initStatus
    def state(self):
        return self._runstate.state

    @property
    @_initStatus
    def startedAt(self):
        """
        When the service started.  Returns None if not running.
        """
        return self._status.startedAt if self._status else None

    @property
    @_initStatus
    def log(self):
        """
        The log of the application.

        :rtype str:
        """
        if self._status:
            return DeployedAppLog(self._status, self._client)

    @property
    def autostart(self):
        """
        Boolean property indicating whether the application automatically
        starts.
        """
        return self._service.launch == self._service.LAUNCH_MODE.AUTO

    @autostart.setter
    def autostart(self, value):
        value = (
            self._service.LAUNCH_MODE.AUTO
            if bool(value)
            else self._service.LAUNCH_MODE.MANUAL
        )
        self._service.launch = value
        self._client.updateServiceProperty(self._service, "Launch")

    @property
    def configurations(self):
        """ """
        return _DeployedAppConfigList(self._service, self._client)

    @configurations.setter
    def configurations(self, configs):
        """
        Set the configurations on a service.  Takes a sequence of
        DeployedAppConfig(s) as the sole argument
        """
        newConfigs = {}
        for config in configs:
            newConfigs[config.filename] = config._config
        self._service.configFiles = newConfigs
        self._client.updateServiceProperty(self._service, "ConfigFiles")

    @_initStatus
    def start(self):
        """
        Starts the application.
        """
        priorState = self._runstate.state
        self._runstate.start()
        if priorState != self._runstate.state:
            LOG.info("[%x] STARTING APP", id(self))
            self._service.desiredState = self._service.STATE.RUN
            self._client.startService(self._service.id)

    @_initStatus
    def stop(self):
        """
        Stops the application.
        """
        priorState = self._runstate.state
        self._runstate.stop()
        if priorState != self._runstate.state:
            LOG.info("[%x] STOPPING APP", id(self))
            self._service.desiredState = self._service.STATE.STOP
            self._client.stopService(self._service.id)

    def restart(self):
        """
        Restarts the application.
        """
        # Make sure the current state is known.
        self.updateStatus()
        # temporary until proper 'reset' functionality is
        # available in controlplane.
        priorState = self._runstate.state
        self._runstate.restart()
        if priorState != self._runstate.state:
            LOG.info("[%x] RESTARTING APP", id(self))
            if self._status:
                self._client.killInstance(self._status.hostId, self._status.id)
            else:
                self._service.desiredState = self._service.STATE.RUN
                self._client.startService(self._service.id)

    def update(self):
        """ """
        self._client.updateService(self._service)

    @property
    def RAMCommitment(self):
        """
        Get the RAM Commitment of the service and trasform it in the byte value.
        RAMCommitment: string in form <number{0-9}><unit{K,M,G,T}>
        """
        match = re.search(
            "(?P<value>[0-9]*\.?[0-9]*)(?P<unit>[k,m,g,t]+)",
            self._service.RAMCommitment,
            re.IGNORECASE,
        )
        if not match:
            return
        RAMCommitment_bytes = int(match.group("value")) * MEM_MULTIPLIER.get(
            match.group("unit").lower()
        )
        return RAMCommitment_bytes


class _DeployedAppConfigList(Sequence):
    """
    Helper class implementing the Sequence protocol.  Instances of
    this class are the object returned by the IApplication's
    'configurations' property.
    """

    def __init__(self, service, client):
        self._service = service
        if not service._data.has_key("ConfigFiles"):
            service._data["ConfigFiles"] = client.getService(service.id)._data[
                "ConfigFiles"
            ]
        self._client = client

    def __getitem__(self, index):
        """
        Return the selected configuration file(s) as indicated by
        the index.  Slice notation is supported.
        """
        # Note: 'index' can be a slice object, but since it's forwarded
        # to the list's __getitem__ method, don't worry about it.
        values = self._service.configFiles.values()
        data = values.__getitem__(index)
        return DeployedAppConfig(self._service, self._client, data)

    def __len__(self):
        """
        Return the number of configuration files.
        """
        return len(self._service.configFiles)

    def __iter__(self):
        """
        Return an iterator that produces DeployedAppConfig objects.
        """
        return _ConfigIterator(self._service, self._client)


class _ConfigIterator(Iterator):
    """
    Helper class to implement iteration of the list of
    IApplicationConfiguration objects.
    """

    def __init__(self, service, client):
        self._service = service
        self._client = client
        if self._service.configFiles is not None:
            self._iter = iter(self._service.configFiles.values())
        else:
            self._iter = iter([])

    def __iter__(self):
        return self

    def next(self):
        return DeployedAppConfig(
            self._service, self._client, self._iter.next()
        )


@implementer(IApplicationConfiguration)
class DeployedAppConfig(object):
    """ """

    def __init__(self, service, client, config):
        self._service = service
        self._client = client
        self._config = config

    @property
    def filename(self):
        """Full path filename of configuration."""
        return self._config.get("Filename")

    @property
    def content(self):
        """Raw contents of the configuration file."""
        return self._config.get("Content")

    @content.setter
    def content(self, content):
        self._config["Content"] = content


@implementer(IApplicationLog)
class DeployedAppLog(object):
    """ """

    def __init__(self, instance, client):
        self._status = instance
        self._client = client

    def last(self, count):
        """
        Returns last count lines of the application log.

        :rtype str:
        """
        result = self._client.getInstanceLog(
            self._status.serviceId, self._status.id
        )
        return result.split("\n")[-count:]


__all__ = (
    "DeployedApp",
    "DeployedAppConfig",
    "DeployedAppLog",
    "DeployedAppLookup",
)
