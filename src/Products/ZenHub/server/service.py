##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections
import logging
import sys
import time
import uuid

import attr

from attr.validators import instance_of
from twisted.internet import defer
from twisted.spread import pb
from zope.component import getUtility
from zope.event import notify

from Products.Zuul.interfaces import IDataRootFactory

from ..errors import RemoteBadMonitor, RemoteException
from .events import ServiceAddedEvent
from .utils import getLogger, import_service_class

_PropagatingErrors = (RemoteException, pb.RemoteError, pb.Error)


class ServiceManager(object):
    """Manages ZenHub service objects."""

    def __init__(self, registry, loader, factory):
        """Initialize a ServiceManager instance.

        :param registry: Stores references to services
        :type registry: Mapping[str, WorkerInterceptor]
        :param loader: Loads and initializes ZenHub services
        :type loader: Callable[[dmd, str, str], HubService]
        :param factory: Builds WorkerInterceptor objects.
        :type factory: Callable[[HubService, str, str], WorkerInterceptor]
        """
        self.__services = registry
        self.__load = loader
        self.__build = factory
        self.__dmd = getUtility(IDataRootFactory)()
        self.__log = getLogger(self)

    @property
    def services(self):
        return self.__services

    def getService(self, name, monitor):
        """Return (a Referenceable to) the named service.

        The name of the service should be the fully qualified module path
        containing the class implementing the service.  For example,

            ZenPacks.zenoss.PythonCollector.services.PythonConfig

        is a fully qualified module path to the PythonConfig zenhub service.
        A class named 'PythonConfig' is expected to be found within the
        module 'PythonConfig'.

        Services found in Products.ZenHub.services can by referred to by
        just their module name.  For example, 'EventService' may be used
        instead of 'Products.ZenHub.services.EventService' to retrieve the
        event service.

        If the service cannot be found, an UnknownServiceError is raised.

        The 'monitor' parameter must be the name of an existing performance
        monitor (aka collector).  If the monitor is unknown, a RemoteBadMonitor
        exception is raised.

        :type str name: Name of the service
        :type str monitor: Name of a performance monitor
        :rtype: WorkerInterceptor
        """
        if (monitor, name) not in self.__services:
            # Sanity check the names given to us
            if not _monitor_exists(self.__dmd, monitor):
                raise RemoteBadMonitor(
                    "Unknown performance monitor: '%s'" % (monitor,), None
                )
            try:
                svc = self.__load(self.__dmd, monitor, name)
                service = self.__build(svc, name, monitor)
                self.__services.add(monitor, name, service)
                notify(ServiceAddedEvent(name, monitor))
            except Exception:
                if self.__log.isEnabledFor(logging.DEBUG):
                    self.__log.exception(
                        "Failed to load service service=%s", name
                    )
                raise
        return self.__services[monitor, name]


def _monitor_exists(dmd, monitor):
    """Return True if the named monitor exists.  Otherwise return False."""
    if dmd.Monitors.Performance._getOb(monitor, False):
        return True
    dmd._p_jar.sync()
    # Try again
    return bool(dmd.Monitors.Performance._getOb(monitor, False))


class ServiceRegistry(collections.Mapping):
    """Registry of WorkerInterceptor objects."""

    def __init__(self):
        self.__services = {}

    def get(self, monitor, name, default=None):
        return self.__services.get((monitor, name), default)

    def __getitem__(self, key):
        return self.__services[key]

    def __iter__(self):
        return iter(self.__services)

    def __len__(self):
        return len(self.__services)

    def add(self, monitor, name, service):
        self.__services[(monitor, name)] = service


class ServiceLoader(object):
    """Load and initialize ZenHub service objects."""

    def __call__(self, dmd, monitor, name):
        cls = import_service_class(name)
        try:
            # Will it construct/initialize?
            return cls(dmd, monitor)
        except Exception:
            # Module can't be used, so unload it.
            # Is this useful?  This would unload the service module, but
            # all other modules imported with the service will remain.
            if cls.__module__ in sys.modules:
                del sys.modules[cls.__module__]
            raise


@attr.s(slots=True, frozen=True)
class ServiceCall(object):
    """Metadata for calling a method on a service."""

    monitor = attr.ib(converter=str)
    """Name of the performance monitor (aka collector)"""

    service = attr.ib(converter=str)
    """Name of the ZenHub service class"""

    method = attr.ib(converter=str)
    """Name of the method to call on the ZenHub service class"""

    args = attr.ib()
    """Positional arguments to the method"""

    kwargs = attr.ib(validator=instance_of(dict))
    """Keyword arguments to the method"""

    id = attr.ib(factory=uuid.uuid4)
    """Unique instance identifier"""

    @args.validator
    def _check_args(self, attribute, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError("args must be a list or tuple")


class ServiceReferenceFactory(object):
    """Builds WorkerInterceptor objects."""

    def __init__(self, cls, routes, executors):
        """Initialize an instance of ServiceReferenceFactory.

        :param cls: The class this factory builds
        :param routes: Map of service calls to executors.
        :type routes: Mapping[ServiceCall, str]
        :param executors: registry of executors
        :type executors: Mapping[str, ServiceExecutor]
        """
        self.__cls = cls
        self.__kwargs = {"routes": routes, "executors": executors}

    def __call__(self, service, name, monitor):
        """Build and return a WorkerInterceptor object.

        :param service: The HubService instance
        :type service: HubService sub-class
        :param str name: Name of the service
        :param str monitor: Name of the performance monitor (collector)
        :rtype: WorkerInterceptor
        """
        args = (service, name, monitor)
        return self.__cls(*args, **self.__kwargs)


class ServiceReference(pb.Referenceable):
    """Delegates remote message handling to another object.

    An 'executor' object is used to execute the method of the named
    service.
    """

    def __init__(self, service, name, monitor, routes, executors):
        """Initialize an instance of ServiceReference.

        :param service: The service object.
        :type service: subclass of HubService
        :param str name: Name of the service.
        :param str monitor: Name of the caller's collection monitor.
        :param routes: Mapping of service calls to executors.
        :type routes: Mapping[ServiceCall, str]
        :param executors: registry of executors.
        :type executors: Mapping[str, ServiceExecutor]
        """
        self.__service = service
        self.__name = name
        self.__monitor = monitor
        self.__executors = executors
        self.__routes = routes
        self.__log = getLogger(self)

        # Required to exist by HubService derived classes.
        self.callTime = 0.0

    @property
    def service(self):
        """Return the service handled by this reference."""
        return self.__service

    @defer.inlineCallbacks
    def remoteMessageReceived(self, broker, message, args, kw):
        """Defer execution of the message to an executor."""
        begin = time.time()
        success = False
        try:
            args = broker.unserialize(args)
            kw = broker.unserialize(kw)
            call = ServiceCall(
                monitor=self.__monitor,
                service=self.__name,
                method=message,
                args=args,
                kwargs=kw,
            )
            executor = self.__get_executor(call)
            self.__log.debug(
                "Begin processing remote message "
                "message=%s service=%s monitor=%s",
                message,
                self.__name,
                self.__monitor,
            )
            result = yield executor.submit(call)
            response = broker.serialize(result, self.perspective)
            success = True
            defer.returnValue(response)
        except _PropagatingErrors:
            raise
        except Exception as ex:
            self.__log.exception(
                "Failed to process remote message "
                "message=%s service=%s monitor=%s error=(%s) %s",
                message,
                self.__name,
                self.__monitor,
                ex.__class__.__name__,
                ex,
            )
            raise pb.Error(
                "Internal ZenHub error: (%s) %s" % (ex.__class__.__name__, ex),
            )
        finally:
            end = time.time()
            elapsed = end - begin
            self.callTime += elapsed
            self.__log.debug(
                "Completed processing remote message "
                "message=%s service=%s monitor=%s status=%s duration=%0.2f",
                message,
                self.__name,
                self.__monitor,
                "OK" if success else "ERROR",
                elapsed,
            )

    def __get_executor(self, call):
        name = self.__routes.get(call)
        if not name:
            raise KeyError(
                "No route found service=%s method=%s"
                % (call.service, call.method),
            )
        executor = self.__executors.get(name)
        if not executor:
            raise KeyError(
                "Executor not registered executor=%s service=%s method=%s"
                % (name, call.service, call.method),
            )
        return executor

    def __getattr__(self, attr):
        """Forward calls to the service object."""
        return getattr(self.__service, attr)


# Note: The name 'WorkerInterceptor' is required to remain compatible with
# the EnterpriseCollector zenpack.
class WorkerInterceptor(ServiceReference):
    """Alias for ServiceReference."""
