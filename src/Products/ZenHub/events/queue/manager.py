##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time

from collections import deque
from itertools import chain

import six

from metrology import Metrology
from metrology.instruments import Gauge
from metrology.registry import registry
from twisted.internet import defer

from Products.ZenEvents.ZenEventClasses import Clear
from Products.ZenHub.interfaces import (
    ICollectorEventTransformer,
    TRANSFORM_DROP,
    TRANSFORM_STOP,
)

from .misc import load_utilities
from .deduping import DeDupingEventQueue
from .deque import DequeEventQueue


class EventQueueManager(object):

    CLEAR_FINGERPRINT_FIELDS = (
        "device",
        "component",
        "eventKey",
        "eventClass",
    )

    def __init__(self, options, log):
        self.options = options
        self.transformers = load_utilities(ICollectorEventTransformer)
        self.log = log
        self.discarded_events = 0
        # TODO: Do we want to limit the size of the clear event dictionary?
        self.clear_events_count = {}
        self._initQueues()
        self._eventsSent = Metrology.meter("collectordaemon.eventsSent")
        self._discardedEvents = Metrology.meter(
            "collectordaemon.discardedEvent"
        )
        self._eventTimer = Metrology.timer("collectordaemon.eventTimer")
        metricNames = {x[0] for x in registry}
        if "collectordaemon.eventQueue" not in metricNames:
            queue = self

            class EventQueueGauge(Gauge):
                @property
                def value(self):
                    return len(queue)

            Metrology.gauge("collectordaemon.eventQueue", EventQueueGauge())

    def __len__(self):
        return (
            len(self.event_queue)
            + len(self.perf_event_queue)
            + len(self.heartbeat_event_queue)
        )

    def _initQueues(self):
        maxlen = self.options.maxqueuelen
        queue_type = (
            DeDupingEventQueue
            if self.options.deduplicate_events
            else DequeEventQueue
        )
        self.event_queue = queue_type(maxlen)
        self.perf_event_queue = queue_type(maxlen)
        self.heartbeat_event_queue = deque(maxlen=1)

    def _transformEvent(self, event):
        for transformer in self.transformers:
            result = transformer.transform(event)
            if result == TRANSFORM_DROP:
                self.log.debug(
                    "event dropped by transform %s: %s", transformer, event
                )
                return None
            if result == TRANSFORM_STOP:
                break
        return event

    def _clearFingerprint(self, event):
        return tuple(
            event.get(field, "") for field in self.CLEAR_FINGERPRINT_FIELDS
        )

    def _removeDiscardedEventFromClearState(self, discarded):
        #
        # There is a particular condition that could cause clear events to
        # never be sent until a collector restart.
        # Consider the following sequence:
        #
        #   1) Clear event added to queue. This is the first clear event of
        #      this type and so it is added to the clear_events_count
        #      dictionary with a count of 1.
        #   2) A large number of additional events are queued until maxqueuelen
        #      is reached, and so the queue starts to discard events including
        #      the clear event from #1.
        #   3) The same clear event in #1 is sent again, however this time it
        #      is dropped because allowduplicateclears is False and the event
        #      has a > 0 count.
        #
        # To resolve this, we are careful to track all discarded events, and
        # remove their state from the clear_events_count dictionary.
        #
        opts = self.options
        if not opts.allowduplicateclears and opts.duplicateclearinterval == 0:
            severity = discarded.get("severity", -1)
            if severity == Clear:
                clear_fingerprint = self._clearFingerprint(discarded)
                if clear_fingerprint in self.clear_events_count:
                    self.clear_events_count[clear_fingerprint] -= 1

    def _addEvent(self, queue, event):
        if self._transformEvent(event) is None:
            return

        allowduplicateclears = self.options.allowduplicateclears
        duplicateclearinterval = self.options.duplicateclearinterval
        if not allowduplicateclears or duplicateclearinterval > 0:
            clear_fingerprint = self._clearFingerprint(event)
            severity = event.get("severity", -1)
            if severity != Clear:
                # A non-clear event - clear out count if it exists
                self.clear_events_count.pop(clear_fingerprint, None)
            else:
                current_count = self.clear_events_count.get(
                    clear_fingerprint, 0
                )
                self.clear_events_count[clear_fingerprint] = current_count + 1
                if not allowduplicateclears and current_count != 0:
                    self.log.debug(
                        "allowduplicateclears dropping clear event %r", event
                    )
                    return
                if (
                    duplicateclearinterval > 0
                    and current_count % duplicateclearinterval != 0
                ):
                    self.log.debug(
                        "duplicateclearinterval dropping clear event %r", event
                    )
                    return

        discarded = queue.append(event)
        self.log.debug("queued event (total of %d) %r", len(queue), event)
        if discarded:
            self.log.warn("discarded event - queue overflow: %r", discarded)
            self._removeDiscardedEventFromClearState(discarded)
            self.discarded_events += 1
            self._discardedEvents.mark()

    def addEvent(self, event):
        self._addEvent(self.event_queue, event)

    def addPerformanceEvent(self, event):
        self._addEvent(self.perf_event_queue, event)

    def addHeartbeatEvent(self, heartbeat_event):
        self.heartbeat_event_queue.append(heartbeat_event)

    @defer.inlineCallbacks
    def sendEvents(self, event_sender_fn):
        # Create new queues - we will flush the current queues and don't want
        # to get in a loop sending events that are queued while we send this
        # batch (the event sending is asynchronous).
        prev_heartbeat_event_queue = self.heartbeat_event_queue
        prev_perf_event_queue = self.perf_event_queue
        prev_event_queue = self.event_queue
        self._initQueues()

        perf_events = []
        events = []
        sent = 0
        try:
            def chunk_events():
                chunk_remaining = self.options.eventflushchunksize
                heartbeat_events = []
                num_heartbeat_events = min(
                    chunk_remaining, len(prev_heartbeat_event_queue)
                )
                for _ in six.moves.range(num_heartbeat_events):
                    heartbeat_events.append(
                        prev_heartbeat_event_queue.popleft()
                    )
                chunk_remaining -= num_heartbeat_events

                perf_events = []
                num_perf_events = min(
                    chunk_remaining, len(prev_perf_event_queue)
                )
                for _ in six.moves.range(num_perf_events):
                    perf_events.append(prev_perf_event_queue.popleft())
                chunk_remaining -= num_perf_events

                events = []
                num_events = min(chunk_remaining, len(prev_event_queue))
                for _ in six.moves.range(num_events):
                    events.append(prev_event_queue.popleft())
                return heartbeat_events, perf_events, events

            heartbeat_events, perf_events, events = chunk_events()
            while heartbeat_events or perf_events or events:
                self.log.debug(
                    "sending %d events, %d perf events, %d heartbeats",
                    len(events),
                    len(perf_events),
                    len(heartbeat_events),
                )
                start = time.time()
                yield event_sender_fn(heartbeat_events + perf_events + events)
                duration = int((time.time() - start) * 1000)
                self._eventTimer.update(duration)
                sent += len(events) + len(perf_events) + len(heartbeat_events)
                self._eventsSent.mark(len(events))
                self._eventsSent.mark(len(perf_events))
                self._eventsSent.mark(len(heartbeat_events))
                heartbeat_events, perf_events, events = chunk_events()

            defer.returnValue(sent)
        except Exception:
            # Restore performance events that failed to send
            perf_events.extend(prev_perf_event_queue)
            discarded_perf_events = self.perf_event_queue.extendleft(
                perf_events
            )
            self.discarded_events += len(discarded_perf_events)
            self._discardedEvents.mark(len(discarded_perf_events))

            # Restore events that failed to send
            events.extend(prev_event_queue)
            discarded_events = self.event_queue.extendleft(events)
            self.discarded_events += len(discarded_events)
            self._discardedEvents.mark(len(discarded_events))

            # Remove any clear state for events that were discarded
            for discarded in chain(discarded_perf_events, discarded_events):
                self.log.debug(
                    "discarded event - queue overflow: %r", discarded
                )
                self._removeDiscardedEventFromClearState(discarded)
            raise
