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

from .base import BaseEventQueue


class DequeEventQueue(BaseEventQueue):
    """
    Event queue implementation backed by a deque. This queue does not
    perform de-duplication of events.
    """

    def __init__(self, maxlen):
        super(DequeEventQueue, self).__init__(maxlen)
        self.__queue = deque()

    def append(self, event):
        # Make sure every processed event specifies the time it was queued.
        if "rcvtime" not in event:
            event["rcvtime"] = time.time()

        discarded = None
        if len(self.__queue) == self.maxlen:
            discarded = self.popleft()
        self.__queue.append(event)
        return discarded

    def popleft(self):
        return self.__queue.popleft()

    def extendleft(self, events):
        if not events:
            return events
        available = self.maxlen - len(self.__queue)
        if not available:
            return events
        to_discard = 0
        if available < len(events):
            to_discard = len(events) - available
        self.__queue.extendleft(reversed(events[to_discard:]))
        return events[:to_discard]

    def __contains__(self, event):
        return event in self.__queue

    def __len__(self):
        return len(self.__queue)

    def __iter__(self):
        return iter(self.__queue)
