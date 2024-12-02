from mock import patch
from unittest import TestCase

from ..deque import DequeEventQueue

PATH = {"src": "Products.ZenHub.events.queue.deque"}


class DequeEventQueueTest(TestCase):
    def setUp(t):
        t.deq = DequeEventQueue(maxlen=10)
        t.event_a, t.event_b = {"name": "event_a"}, {"name": "event_b"}

    def test_init(t):
        maxlen = 100
        deq = DequeEventQueue(maxlen=maxlen)
        t.assertEqual(deq.maxlen, maxlen)

    @patch("{src}.time".format(**PATH))
    def test_append(t, time):
        event = {}
        deq = DequeEventQueue(maxlen=10)

        ret = deq.append(event)

        # append sets the time the event was added to the queue
        t.assertEqual(event["rcvtime"], time.time())
        t.assertEqual(ret, None)

    def test_append_pops_and_returns_leftmost_if_full(t):
        event_a, event_b = {"name": "event_a"}, {"name": "event_b"}
        deq = DequeEventQueue(maxlen=1)

        deq.append(event_a)
        ret = deq.append(event_b)

        t.assertIn(event_b, deq)
        t.assertNotIn(event_a, deq)
        t.assertEqual(ret, event_a)

    @patch("{src}.time".format(**PATH))
    def test_popleft(t, time):
        t.deq.append(t.event_a)
        t.deq.append(t.event_b)

        ret = t.deq.popleft()

        t.assertEqual(ret, t.event_a)

    @patch("{src}.time".format(**PATH))
    def test_extendleft(t, time):
        """WARNING: extendleft does NOT add timestamps, as .append does
        is this behavior is intentional?
        """
        event_c = {"name": "event_c"}
        t.deq.append(event_c)
        t.assertEqual(list(t.deq), [event_c])
        events = [t.event_a, t.event_b]

        ret = t.deq.extendleft(events)

        t.assertEqual(ret, [])
        t.assertEqual(list(t.deq), [t.event_a, t.event_b, event_c])
        """
        # to validate all events get timestamps
        t.assertEqual(
            list(t.deq),
            [{'name': 'event_a', 'rcvtime': time.time.return_value},
             {'name': 'event_b', 'rcvtime': time.time.return_value},
             {'name': 'event_c', 'rcvtime': time.time.return_value},
            ]
        """

    def test_extendleft_returns_events_if_falsey(t):
        ret = t.deq.extendleft(False)
        t.assertEqual(ret, False)
        ret = t.deq.extendleft([])
        t.assertEqual(ret, [])
        ret = t.deq.extendleft(0)
        t.assertEqual(ret, 0)

    def test_extendleft_returns_extra_events_if_nearly_full(t):
        t.deq.maxlen = 3
        t.deq.extendleft([t.event_a, t.event_b])
        event_c, event_d = {"name": "event_c"}, {"name": "event_d"}
        events = [event_c, event_d]

        ret = t.deq.extendleft(events)

        t.assertEqual(list(t.deq), [event_d, t.event_a, t.event_b])
        t.assertEqual(ret, [event_c])

    def test___len__(t):
        ret = len(t.deq)
        t.assertEqual(ret, 0)
        t.deq.extendleft([t.event_a, t.event_b])
        t.assertEqual(len(t.deq), 2)

    def test___iter__(t):
        t.deq.extendleft([t.event_a, t.event_b])
        ret = [event for event in t.deq]
        t.assertEqual(ret, [t.event_a, t.event_b])
