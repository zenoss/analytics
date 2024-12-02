##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class BaseEventQueue(object):
    def __init__(self, maxlen):
        self.maxlen = maxlen

    def append(self, event):
        """
        Appends the event to the queue.

        @param event: The event.
        @return: If the queue is full, this will return the oldest event
                 which was discarded when this event was added.
        """
        raise NotImplementedError()

    def popleft(self):
        """
        Removes and returns the oldest event from the queue. If the queue
        is empty, raises IndexError.

        @return: The oldest event from the queue.
        @raise IndexError: If the queue is empty.
        """
        raise NotImplementedError()

    def extendleft(self, events):
        """
        Appends the events to the beginning of the queue (they will be the
        first ones removed with calls to popleft). The list of events are
        expected to be in order, with the earliest queued events listed
        first.

        @param events: The events to add to the beginning of the queue.
        @type events: list
        @return A list of discarded events that didn't fit on the queue.
        @rtype list
        """
        raise NotImplementedError()

    def __len__(self):
        """
        Returns the length of the queue.

        @return: The length of the queue.
        """
        raise NotImplementedError()

    def __iter__(self):
        """
        Returns an iterator over the elements in the queue (oldest events
        are returned first).
        """
        raise NotImplementedError()
