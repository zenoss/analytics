##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from collections import deque
from twisted.internet import defer


class ZenHubWorklist(object):
    """Implements a priority queue with a fair retrieval algorithm.

    Items may be pushed into the queue in any order.  Each item is assigned a
    priority and stored in FIFO order by priority.

    ZenHubWorklist maintains a deterministic ordering of priorities.  When
    an item is popped, the next priority in order is selected and the first
    item with that priority is returned to the caller.  The ordering is
    designed such that higher priorities are selected more frequently than
    lower priorities.  It is never the case that all higher priority items
    are popped before lower priority items are popped.
    """

    def __init__(self, priority_selection):
        """Initialize a ZenHubWorklist object.

        :type priority_selection: PrioritySelection
        """
        # All jobs priority selection
        self.__selection = priority_selection

        # Associate a queue with each priority
        self.__queues = {
            priority: deque() for priority in self.__selection.priorities
        }

        # Queue of pending requests for data
        self.__waiting = []

    def __len__(self):
        return sum(len(v) for v in self.__queues.itervalues())

    def __cancel_pop(self, d):
        self.__waiting.remove(d)

    def __pop(self):
        """Return the next item by priority.

        If no items are available, None is returned.

        :rtype: Union[Any, None]
        """
        available = self.__selection.available
        while sum(len(self.__queues[p]) for p in available):
            priority = next(self.__selection)
            queue = self.__queues[priority]
            if len(queue):
                return queue.popleft()

    def pop(self):
        """Return a deferred which fires when an item is available.

        :rtype: defer.Deferred
        """
        item = self.__pop()
        if item is not None:
            return defer.succeed(item)
        d = defer.Deferred(canceller=self.__cancel_pop)
        self.__waiting.append(d)
        return d

    def push(self, priority, item):
        """Add item to the worklist.

        :type item: Any
        :param priority: The priority of the item
        :type priority: Sortable[T]
        """
        self.__queues[priority].append(item)
        self.__notify_waiting_request()

    def pushfront(self, priority, item):
        """Add item to the front of the worklist.

        Use this method to return jobs to the worklist.

        :type item: Any
        :param priority: The priority of the item
        :type priority: Sortable[T]
        """
        self.__queues[priority].appendleft(item)
        self.__notify_waiting_request()

    def __notify_waiting_request(self):
        if not self.__waiting:
            return
        item = self.__pop()
        if item is not None:
            self.__waiting.pop(0).callback(item)
