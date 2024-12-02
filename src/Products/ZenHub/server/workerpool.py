##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from collections import Container, Iterable, Sized

from twisted.internet import defer
from twisted.spread import pb
from zope.component import adapter, provideHandler

from .events import ReportWorkerStatus
from .utils import getLogger


class WorkerPool(Container, Iterable, Sized):
    """Pool of ZenHubWorker RemoteReference objects."""

    def __init__(self, name):
        """Initialize a WorkerPool instance.

        ZenHubWorker will specify a "worklist" to accept tasks from.  The
        name of the worklist is given by the 'name' parameter.

        :param str name: Name of the "worklist" associated with this pool.
        """
        # __available contains workers (by ID) available for work
        self.__available = WorkerAvailabilityQueue()

        # Worker refs by worker.name
        # type: {str: Worker}
        self.__workers = {}

        self.__name = name
        self.__log = getLogger(self)
        # Declare a handler for ReportWorkerStatus events
        provideHandler(self.handleReportStatus)

    @property
    def name(self):
        return self.__name

    def get(self, name, default=None):  # type: (name: str) -> Worker | None
        """Return the worker having the given name."""
        return self.__workers.get(name, default)

    def add(self, worker):  # type: (worker: Worker) -> None
        """Add a worker to the pool.

        The added worker will replace any existing worker that has the
        same `name` attribute value.

        Added workers are not available to hire until `ready` is called.

        @type worker: Products.ZenHub.server.worker.Worker
        """
        name = worker.name
        replaced = False
        stored_worker = self.__workers.get(name)
        if stored_worker is worker:
            return
        elif stored_worker is not None:
            replaced = True
            self.__discard(name)
        self.__workers[name] = worker
        self.__log.debug(
            "%s worker  worker=%s total-workers=%s",
            "added" if not replaced else "replaced",
            worker.name,
            len(self.__workers),
        )

    def remove(self, worker):
        """Remove a worker from the pool.

        @param worker {RemoteReference} A reference to the remote worker
        """
        stored_worker = self.__workers.get(worker.name)
        if stored_worker is not worker:
            self.__log.debug(
                "cannot remove unknown worker  worker=%s", worker.name
            )
            return
        self.__discard(worker.name)
        self.__log.debug(
            "removed worker  worker=%s total-workers=%s",
            worker.name,
            len(self.__workers),
        )

    def ready(self, worker):
        """Make a worker available to hire.

        @param worker: A reference to the remote worker
        @type worker: RemoteReference
        """
        if worker.name not in self.__workers:
            self.__log.debug("retired  worker=%s", worker.name)
            return
        if worker.name not in self.__available:
            self.__available.add(worker.name)
            self.__log.debug("available to hire  worker=%s", worker.name)

    @property
    def available(self):
        """Return the number of workers available for work."""
        return len(self.__available)

    @defer.inlineCallbacks
    def hire(self):  # type: () -> Worker
        """Return a valid worker.

        This method blocks until a worker is available.
        """
        while True:
            name = yield self.__available.pop()
            try:
                worker = self.__workers[name]
                # Ping the worker to test whether it still exists
                yield worker.remote.callRemote("ping")
            except KeyError:
                self.__log.error(
                    "available worker doesn't exist  worker=%s", name
                )
            except (
                pb.RemoteError,
                pb.PBConnectionLost,
                pb.DeadReferenceError,
            ) as ex:
                msg = _bad_worker_messages.get(type(ex))
                self.__log.warning(msg, worker.name)
                self.__discard(name)
            except Exception:
                self.__log.exception("unexpected error")
                self.__discard(name)
            else:
                self.__log.debug("hired worker  worker=%s", worker.name)
                defer.returnValue(worker)

    @adapter(ReportWorkerStatus)
    def handleReportStatus(self, event):
        """Instructs workers to report their status.

        Returns a DeferredList that fires when all the workers have
        completed reporting their status.
        """
        deferreds = []
        for worker in self.__workers.viewvalues():
            dfr = worker.remote.callRemote("reportStatus")
            dfr.addErrback(
                lambda ex, name=worker.name: self.__log.error(
                    "Failed to report status (%s): %s", name, ex
                ),
            )
            deferreds.append(dfr)
        return defer.DeferredList(deferreds)

    def __discard(self, name):
        if name in self.__workers:
            del self.__workers[name]
        self.__available.discard(name)

    def __contains__(self, worker):
        """Return True if worker is present, else False is returned.

        Note: the worker is expected to have a 'name' attribute.

        @param worker {RemoteReference} A reference to the remote worker
        """
        return self.__workers.get(worker.name) is worker

    def __len__(self):
        return len(self.__workers)

    def __iter__(self):
        return (
            worker
            for worker in self.__workers.itervalues()
            if worker is not None
        )


_bad_worker_messages = {
    pb.PBConnectionLost: "worker failed ping test  worker=%s",
    pb.DeadReferenceError: (
        "worker no longer available (dead reference)  worker=%s"
    ),
    pb.RemoteError: "worker is restarting  worker=%s",
}


class WorkerAvailabilityQueue(defer.DeferredQueue):
    """Extends defer.DeferredQueue with more set-like behavior."""

    def __len__(self):
        return len(self.pending)

    def __contains__(self, item):
        return item in self.pending

    # Alias pop to get -- DeferredQueue.get removes the value from the queue.
    pop = defer.DeferredQueue.get

    def add(self, item):
        if item not in self.pending:
            self.put(item)

    def discard(self, item):
        if item in self.pending:
            self.pending.remove(item)
