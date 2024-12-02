##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections
import logging

from functools import partial

from twisted.internet import defer, reactor, task

from ..errors import HubDown

log = logging.getLogger("zen.eventclient")

# field size limits for events
DEFAULT_LIMIT = 524288  # 512k
LIMITS = {"summary": 256, "message": 4096}


class EventClient(object):
    """
    Manages sending events to ZenHub's event service.
    """

    def __init__(self, options, queue, builder, servicefactory):
        """
        Initialize an EventClient instance.
        """
        self.__queue = queue
        self.__builder = builder
        self.__factory = servicefactory

        self.__flushinterval = options.eventflushseconds
        self.__flushchunksize = options.eventflushchunksize
        self.__maxqueuelength = options.maxqueuelen
        self.__limit = options.maxqueuelen * options.queueHighWaterMark

        self.__task = task.LoopingCall(self._push)
        self.__taskd = None
        self.__pause = None
        self.__pushing = False
        self.__stopping = False

        self.counters = collections.Counter()

    def start(self):  # type: () -> None
        """Start the event client."""
        # Note: the __taskd deferred is called when __task is stopped
        self.__taskd = self.__task.start(self.__flushinterval, now=False)
        self.__taskd.addCallback(self._last_push)

    def stop(self):  # type: () -> defer.Deferred
        """Stop the event client."""
        self.__stopping = True
        if self.__pause is None:
            self.__pause = defer.Deferred()
        self.__task.stop()
        return self.__pause

    def sendEvents(self, events):  # (Sequence[dict]) -> defer.DeferredList
        return defer.DeferredList([self.sendEvent(event) for event in events])

    @defer.inlineCallbacks
    def sendEvent(self, event, **kw):
        """
        Add event to queue of events to be sent.
        If we have an event service then process the queue.
        """
        if not reactor.running:
            defer.returnValue(None)

        # If __pause is not None, yield it which blocks this
        # method until the deferred is called and the yield returns.
        if self.__pause:
            yield self.__pause

        built_event = self.__builder(event, **kw)
        self.__queue.addEvent(built_event)
        self.counters["eventCount"] += 1

    def sendHeartbeat(self, event):
        self.__queue.addHeartbeatEvent(event)

    @defer.inlineCallbacks
    def _last_push(self, task):
        yield self._push()

    @defer.inlineCallbacks
    def _push(self):
        """
        Flush events to ZenHub.
        """
        if len(self.__queue) >= self.__limit and not self.__pause:
            log.debug(
                "pause accepting new events; queue length at or "
                "exceeds high water mark (%s >= %s)",
                len(self.__queue),
                self.__limit,
            )
            self.__pause = defer.Deferred()

        if self.__pushing:
            log.debug("skipping event sending - previous call active.")
            defer.returnValue("push pending")

        try:
            self.__pushing = True

            discarded_events = self.__queue.discarded_events
            if discarded_events:
                log.error(
                    "discarded oldest %d events because maxqueuelen was "
                    "exceeded: %d/%d",
                    discarded_events,
                    discarded_events + self.__maxqueuelength,
                    self.__maxqueuelength,
                )
                self.counters["discardedEvents"] += discarded_events
                self.__queue.discarded_events = 0

            eventsvc = yield self.__factory()
            send_events_fn = partial(eventsvc.callRemote, "sendEvents")
            count = yield self.__queue.sendEvents(send_events_fn)
            if count > 0:
                log.debug("sent %d event%s", count, "s" if count > 1 else "")
        except HubDown as ex:
            log.warn("event service unavailable: %s", ex)
        except Exception as ex:
            log.exception("failed to send event: %s", ex)
            # let the reactor have time to clean up any connection
            # errors and make callbacks
            yield task.deferLater(reactor, 0, lambda: None)
        finally:
            self.__pushing = False
            if self.__pause and len(self.__queue) < self.__limit:
                # Don't log the 'resume' message during a shutdown is
                # confusing to avoid confusion.
                if not self.__stopping:
                    log.debug(
                        "resume accepting new events; queue length below "
                        "high water mark (%s < %s)",
                        len(self.__queue),
                        self.__limit,
                    )
                pause, self.__pause = self.__pause, None
                pause.callback("Queue length below high water mark")
