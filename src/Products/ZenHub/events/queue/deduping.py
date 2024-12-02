##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time

from collections import OrderedDict

from Products.ZenHub.interfaces import ICollectorEventFingerprintGenerator

from .base import BaseEventQueue
from .fingerprint import DefaultFingerprintGenerator
from .misc import load_utilities


class DeDupingEventQueue(BaseEventQueue):
    """
    Event queue implementation backed by a OrderedDict. This queue performs
    de-duplication of events (when an event with the same fingerprint is
    seen, the 'count' field of the event is incremented by one instead of
    sending an additional event).
    """

    def __init__(self, maxlen):
        super(DeDupingEventQueue, self).__init__(maxlen)
        self.__fingerprinters = load_utilities(
            ICollectorEventFingerprintGenerator
        )
        if not self.__fingerprinters:
            self.__fingerprinters = [DefaultFingerprintGenerator()]
        self.__queue = OrderedDict()

    def append(self, event):
        # Make sure every processed event specifies the time it was queued.
        if "rcvtime" not in event:
            event["rcvtime"] = time.time()

        fingerprint = self._fingerprint_event(event)
        if fingerprint in self.__queue:
            # Remove the currently queued item - we will insert again which
            # will move to the end.
            current_event = self.__queue.pop(fingerprint)
            event["count"] = current_event.get("count", 1) + 1
            event["firstTime"] = self._first_time(current_event, event)
            self.__queue[fingerprint] = event
            return

        discarded = None
        if len(self.__queue) == self.maxlen:
            discarded = self.popleft()

        self.__queue[fingerprint] = event
        return discarded

    def popleft(self):
        try:
            return self.__queue.popitem(last=False)[1]
        except KeyError:
            # Re-raise KeyError as IndexError for common interface across
            # queues.
            raise IndexError()

    def extendleft(self, events):
        # Attempt to de-duplicate with events currently in queue
        events_to_add = []
        for event in events:
            fingerprint = self._fingerprint_event(event)
            if fingerprint in self.__queue:
                current_event = self.__queue[fingerprint]
                current_event["count"] = current_event.get("count", 1) + 1
                current_event["firstTime"] = self._first_time(
                    current_event, event
                )
            else:
                events_to_add.append(event)

        if not events_to_add:
            return events_to_add
        available = self.maxlen - len(self.__queue)
        if not available:
            return events_to_add
        to_discard = 0
        if available < len(events_to_add):
            to_discard = len(events_to_add) - available
        old_queue, self.__queue = self.__queue, OrderedDict()
        for event in events_to_add[to_discard:]:
            self.__queue[self._fingerprint_event(event)] = event
        for fingerprint, event in old_queue.iteritems():
            self.__queue[fingerprint] = event
        return events_to_add[:to_discard]

    def __contains__(self, event):
        return self._fingerprint_event(event) in self.__queue

    def __len__(self):
        return len(self.__queue)

    def __iter__(self):
        return self.__queue.itervalues()

    def _fingerprint_event(self, event):
        for fingerprinter in self.__fingerprinters:
            fingerprint = fingerprinter.generate(event)
            if fingerprint is not None:
                break
        return fingerprint

    def _first_time(self, event1, event2):
        def first(evt):
            return evt.get("firstTime", evt["rcvtime"])

        return min(first(event1), first(event2))
