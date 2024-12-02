##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.cred import portal
from twisted.internet.endpoints import serverFromString
from zope.component import getUtility

from Products.ZenUtils.PBUtil import setKeepAlive

from .auth import HubRealm
from .avatar import HubAvatar
from .broker import ZenPBServerFactory
from .interface import IHubServerConfig
from .router import ServiceCallRouter
from .service import (
    ServiceLoader,
    ServiceManager,
    ServiceReferenceFactory,
    ServiceRegistry,
    WorkerInterceptor,
)
from .utils import import_name, TCPDescriptor
from .workerpool import WorkerPool


# Global reference to _executor instances
_executors = {}


def start_server(reactor, server_factory):
    """Start the PerspectiveBroker server.

    :param reactor: The Twisted reactor.
    :param server_factory: Used by Twisted to create PB server.
    :type server_factory: .broker.ZenPBServerFactory
    """
    # Start the executors:
    global _executors
    for executor in _executors.values():
        executor.start(reactor)

    # Retrieve the server config object.
    config = getUtility(IHubServerConfig)

    # Build the network descriptor for the PerspectiveBroker server.
    pb_descriptor = TCPDescriptor.with_port(config.pbport)

    # Construct the PerspectiveBroker server
    pb_server = serverFromString(reactor, pb_descriptor)

    # Begin listening
    dfr = pb_server.listen(server_factory)

    # set the keep-alive config on the server's listening socket
    dfr.addCallback(lambda listener: setKeepAlive(listener.socket))


def stop_server():
    # Stop the executors:
    global _executors
    for executor in _executors.values():
        executor.stop()


def make_server_factory(pools, manager, authenticators):
    """Return a ZenPBServerFactory instance.

    :param service_registry: Registry of loaded ZenHub services
    :type service_registry: Mapping[str, HubServer]
    :param authenticators: Used to authenticate clients.
    :type authenticators: Sequence[Authenticator]
    """
    # Build the authentication pieces
    avatar = HubAvatar(manager, pools)
    realm = HubRealm(avatar)
    hubportal = portal.Portal(realm, authenticators)

    # Return the initialized Perspective Broker server factory.
    return ZenPBServerFactory(hubportal)


def make_service_manager(pools):
    # Retrieve the server config object.
    config = getUtility(IHubServerConfig)

    registry = ServiceRegistry()
    routes = ServiceCallRouter.from_config(config.routes)

    # Build the executors;
    # returns a dict having <executor-name>: <executor-instance>
    executors = make_executors(config, pools)

    # Build the ZenHub service manager
    loader = ServiceLoader()
    factory = ServiceReferenceFactory(WorkerInterceptor, routes, executors)
    return ServiceManager(registry, loader, factory)


def make_pools():
    # Retrieve the server config object.
    config = getUtility(IHubServerConfig)
    # Registry of references to zenhubworker connections
    # <pool-name>: WorkerPool
    return {name: WorkerPool(name) for name in config.pools.keys()}


def make_executors(config, pools):
    global _executors
    for name, spec in config.executors.items():
        modpath, clsname = spec.split(":", 1)
        cls = import_name(modpath, clsname)
        executor = cls.create(name, config=config, pool=pools.get(name))
        _executors[name] = executor
    return _executors
