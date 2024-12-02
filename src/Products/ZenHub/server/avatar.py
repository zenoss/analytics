##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import os

from twisted.spread import pb

from ..errors import RemoteBadMonitor
from .exceptions import UnknownServiceError
from .utils import getLogger
from .worker import Worker


class HubAvatar(pb.Avatar):
    """Manages the connection between clients and ZenHub."""

    def __init__(self, services, pools):
        """Initialize an instance of HubAvatar.

        :param services: The service manager
        :type services: .service.ServiceManager
        :param pools: Registry of zenhubworker remote references
        :type pools: Mapping[str, WorkerPool]
        """
        self.__services = services
        self.__pools = pools
        self.__log = getLogger(self)

    def perspective_ping(self):
        """Return 'pong'."""
        return "pong"

    def perspective_getHubInstanceId(self):
        """Return the Control Center instance ID the running service."""
        return os.environ.get("CONTROLPLANE_INSTANCE_ID", "Unknown")

    def perspective_getService(
        self, name, monitor=None, listener=None, options=None
    ):
        """Return a reference to a ZenHub service.

        It also associates the service with a collector so that changes can be
        pushed back out to collectors.

        :param str name: The name of the service, e.g. "EventService"
        :param str monitor: The name of a collector, e.g. "localhost"
        :param listener: A remote reference to the client
        :type listener: twisted.spread.pb.RemoteReference
        :return: A reference to a service
        :rtype: .service.WorkerInterceptor
        """
        try:
            service = self.__services.getService(name, monitor)
        except RemoteBadMonitor:
            if self.__log.isEnabledFor(logging.DEBUG):
                self.__log.error("Monitor unknown monitor=%s", monitor)
            # This is a valid remote exception, so let it go through
            # to the collector daemon to handle
            raise
        except UnknownServiceError:
            self.__log.error("Service not found service=%s", name)
            raise
        except Exception as ex:
            self.__log.exception("Failed to load service service=%s", name)
            raise pb.Error(str(ex))
        else:
            if service is not None and listener:
                service.addListener(listener, options)
            return service

    def perspective_reportForWork(self, remote, name, worklistId):
        """Allow a worker to register for work.

        :param workerref: Reference to zenhubworker
        :type workerref: twisted.spread.pb.RemoteReference
        :param str name: The name of the worker
        :param str worklistId: The worker will work jobs from this worklist
        :rtype: None
        """
        pool = self._get_pool(worklistId, name)
        worker = Worker(name=name, remote=remote)
        try:
            pool.add(worker)
            pool.ready(worker)
        except Exception as ex:
            self.__log.exception(
                "failed to add worker  worker=%s worklist=%s", name, worklistId
            )
            raise pb.Error(
                "Internal ZenHub error: %s: %s" % (ex.__class__, ex),
            )
        self.__log.info(
            "registered worker  worker=%s worklist=%s", name, worklistId
        )
        remote.notifyOnDisconnect(
            lambda ref, n=name, q=worklistId: self._remove_worker(ref, n, q)
        )

    def perspective_resignFromWork(self, name, worklistId):
        """Allow a worker to unregister itself from work.

        :param str name: The name of the worker
        :param str worklistId: The worker will work jobs from this worklist
        :rtype: None
        """
        pool = self._get_pool(worklistId, name)
        worker = self._get_worker(pool, name, worklistId)
        if worker is not None:
            pool.remove(worker)
            del worker  # maybe this works...?
            self.__log.info(
                "unregistered worker  worker=%s worklist=%s", name, worklistId
            )

    def _get_pool(self, worklistId, name):
        pool = self.__pools.get(worklistId)
        if pool is None:
            self.__log.error(
                "worker asked to resign from unknown worklist  "
                "worker=%s worklist=%s",
                name,
                worklistId,
            )
            raise pb.Error("No such worklist: %s" % worklistId)
        return pool

    def _get_worker(self, pool, name, worklistId):
        worker = pool.get(name)
        if worker is None:
            self.__log.debug(
                "unknown worker  worker=%s worklist=%s", name, worklistId
            )
        return worker

    def _remove_worker(self, remote, name, worklistId):
        # Note that 'remote' is ignored.
        pool = self.__pools.get(worklistId)
        if pool is None:
            return
        worker = self._get_worker(pool, name, worklistId)
        if worker is not None:
            pool.remove(worker)
        self.__log.info(
            "worker disconnected  worker=%s worklist=%s", name, worklistId
        )
