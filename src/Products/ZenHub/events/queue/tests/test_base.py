from unittest import TestCase

from ..base import BaseEventQueue


class BaseEventQueueTest(TestCase):
    def setUp(t):
        t.beq = BaseEventQueue(maxlen=5)

    def test_init(t):
        base_event_queue = BaseEventQueue(maxlen=5)
        t.assertEqual(base_event_queue.maxlen, 5)

    def test_append(t):
        with t.assertRaises(NotImplementedError):
            t.beq.append("event")

    def test_popleft(t):
        with t.assertRaises(NotImplementedError):
            t.beq.popleft()

    def test_extendleft(t):
        with t.assertRaises(NotImplementedError):
            t.beq.extendleft(["event_a", "event_b"])

    def test___len__(t):
        with t.assertRaises(NotImplementedError):
            len(t.beq)

    def test___iter__(t):
        with t.assertRaises(NotImplementedError):
            for _ in t.beq:
                pass
