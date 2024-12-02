##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from time import time
from itertools import chain
from functools import wraps

from twisted.internet.defer import inlineCallbacks, returnValue
from ZODB.POSException import POSKeyError
from zope.component import getUtility, getUtilitiesFor, subscribers

from zenoss.protocols.protobufs.zep_pb2 import (
    SEVERITY_CLEAR,
    SEVERITY_CRITICAL,
)

from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)

from .interfaces import (
    FILTER_EXCLUDE,
    FILTER_INCLUDE,
    IInvalidationFilter,
    IInvalidationOid,
    IInvalidationProcessor,
)
from .invalidations import INVALIDATIONS_PAUSED

log = logging.getLogger("zen.zenhub.invalidations")


class InvalidationManager(object):
    _invalidation_paused_event = {
        "summary": "Invalidation processing is "
        "currently paused. To resume, set "
        "'dmd.pauseHubNotifications = False'",
        "severity": SEVERITY_CRITICAL,
        "eventkey": INVALIDATIONS_PAUSED,
    }

    _invalidation_unpaused_event = {
        "summary": "Invalidation processing unpaused",
        "severity": SEVERITY_CLEAR,
        "eventkey": INVALIDATIONS_PAUSED,
    }

    def __init__(
        self,
        dmd,
        syncdb,
        poll_invalidations,
        send_event,
        poll_interval=30,
    ):
        self.__dmd = dmd
        self.__syncdb = syncdb
        self.__poll_invalidations = poll_invalidations
        self.__send_event = send_event
        self.poll_interval = poll_interval
        self._queue = set()

        self._currently_paused = False
        self.totalEvents = 0
        self.totalTime = 0

        self._invalidation_filters = self.initialize_invalidation_filters(
            self.__dmd
        )
        self.processor = getUtility(IInvalidationProcessor)
        app = self.__dmd.getPhysicalRoot()
        self.invalidation_pipeline = InvalidationPipeline(
            app, self._invalidation_filters, self._queue
        )

    @staticmethod
    def initialize_invalidation_filters(ctx):
        """
        Return initialized IInvalidationFilter objects in a list.

        :param ctx: Used to initialize the IInvalidationFilter objects.
        :type ctx: DataRoot
        :return: Initialized IInvalidationFilter objects
        :rtype: List[IInvalidationFilter]
        """
        try:
            filters = (f for n, f in getUtilitiesFor(IInvalidationFilter))
            invalidation_filters = []
            for fltr in sorted(
                filters, key=lambda f: getattr(f, "weight", 100)
            ):
                fltr.initialize(ctx)
                invalidation_filters.append(fltr)
            log.info(
                "registered %s invalidation filters.",
                len(invalidation_filters),
            )
            log.info("invalidation filters: %s", invalidation_filters)
            return invalidation_filters
        except Exception:
            log.exception("error in initialize_invalidation_filters")

    @inlineCallbacks
    def process_invalidations(self):
        """
        Periodically process database changes.

        Synchronize with the database, and poll invalidated oids from it,
        filter the oids,  send them to the invalidation_processor

        @return: None
        """
        try:
            now = time()
            yield self._syncdb()
            if self._paused():
                returnValue(None)

            oids = self._poll_invalidations()
            if not oids:
                log.debug("no invalidations found")
                returnValue(None)

            for oid in oids:
                yield self.invalidation_pipeline.run(oid)

            handled, ignored = yield self.processor.processQueue(self._queue)
            log.debug(
                "processed invalidations  "
                "handled-count=%d, ignored-count=%d",
                handled,
                ignored,
            )
            self._queue.clear()
        except Exception:
            log.exception("error in process_invalidations")
        finally:
            self.totalEvents += 1
            self.totalTime += time() - now

    @inlineCallbacks
    def _syncdb(self):
        try:
            log.debug("syncing with ZODB ...")
            yield self.__syncdb()
            log.debug("synced with ZODB")
        except Exception:
            log.warn("Unable to poll invalidations")

    def _paused(self):
        if not self._currently_paused:
            if self.__dmd.pauseHubNotifications:
                self._currently_paused = True
                log.info("invalidation processing has been paused")
                self._send_event(self._invalidation_paused_event)
                return True
            else:
                return False

        else:
            if self.__dmd.pauseHubNotifications:
                log.debug("invalidation processing is paused")
                return True
            else:
                self._currently_paused = False
                log.info("invalidation processing has been unpaused")
                self._send_event(self._invalidation_unpaused_event)
                return False

    def _poll_invalidations(self):
        """pull a list of invalidated object oids from the database"""
        try:
            log.debug("poll invalidations from dmd.storage")
            return self.__poll_invalidations()
        except Exception:
            log.exception("failed to poll invalidations")

    @inlineCallbacks
    def _send_event(self, event):
        yield self.__send_event(event)


class InvalidationPipeline(object):
    """A Pipeline that applies filters and transforms to an oid
    Then passes the transformed/expanded list of oids
    to the InvalidationProcessor processQueue
    """

    def __init__(self, app, filters, sink):
        self.__app = app
        self.__filters = filters
        self.__sink = sink
        self.__pipeline = self._build_pipeline()

    def _build_pipeline(self):
        sink = set_sink(self.__sink)
        pipeline = oid_to_obj(
            self.__app, sink, filter_obj(self.__filters, transform_obj(sink))
        )
        return pipeline

    def run(self, invalidation):
        try:
            self.__pipeline.send(invalidation)
        except Exception:
            log.exception("error in run")
            self.__pipeline = self._build_pipeline()


def coroutine(func):
    """Decorator for initializing a generator as a coroutine."""

    @wraps(func)
    def start(*args, **kw):
        coro = func(*args, **kw)
        coro.next()
        return coro

    return start


@coroutine
def oid_to_obj(app, sink, target):
    while True:
        oid = yield
        # Include oids that are missing from the database
        try:
            obj = app._p_jar[oid]
        except POSKeyError:
            sink.send([oid])
            continue
        # Exclude any unmatched types
        if not isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
            continue
        # Include deleted oids
        try:
            obj = obj.__of__(app.zport.dmd).primaryAq()
        except (AttributeError, KeyError):
            sink.send([oid])
            continue

        target.send((oid, obj))


@coroutine
def filter_obj(filters, target):
    while True:
        oid, obj = yield
        included = True
        for fltr in filters:
            result = fltr.include(obj)
            if result is FILTER_INCLUDE:
                log.debug("filter %s INCLUDE %s:%s", fltr, str(oid), obj)
                break
            if result is FILTER_EXCLUDE:
                log.debug("filter %s EXCLUDE %s:%s", fltr, str(oid), obj)
                included = False
                break
        if included:
            log.debug("filters FALLTHROUGH: %s", obj)
            target.send((oid, obj))


@coroutine
def transform_obj(target):
    while True:
        oid, obj = yield

        # First, get any subscription adapters registered as transforms
        adapters = subscribers((obj,), IInvalidationOid)
        # Next check for an old-style (regular adapter) transform
        try:
            adapters = chain(adapters, (IInvalidationOid(obj),))
        except TypeError:
            # No old-style adapter is registered
            pass
        transformed = set()
        for adapter in adapters:
            o = adapter.transformOid(oid)
            if isinstance(o, str):
                transformed.add(o)
            elif hasattr(o, "__iter__"):
                # If the transform didn't give back a string, it should have
                # given back an iterable
                transformed.update(o)
        # Get rid of any useless Nones
        transformed.discard(None)
        # Get rid of the original oid, if returned. We don't want to use it IF
        # any transformed oid came back.
        transformed.discard(oid)
        target.send(transformed or (oid,))


@coroutine
def set_sink(output_set):
    while True:
        input = yield
        output_set.update(input)
