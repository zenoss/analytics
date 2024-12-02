from mock import Mock, patch
from unittest import TestCase

from ..deduping import DeDupingEventQueue
from ..fingerprint import DefaultFingerprintGenerator

PATH = {"src": "Products.ZenHub.events.queue.deduping"}


class DeDupingEventQueueTest(TestCase):
    def setUp(t):
        t.ddeq = DeDupingEventQueue(maxlen=10)
        t.event_a, t.event_b = {"name": "event_a"}, {"name": "event_b"}

    @patch("{src}.load_utilities".format(**PATH))
    def test_init(t, load_utilities):
        load_utilities.return_value = []
        ddeq = DeDupingEventQueue(maxlen=10)
        t.assertEqual(ddeq.maxlen, 10)

        default = DefaultFingerprintGenerator()
        expected = default.generate(t.event_a)
        actual = ddeq._fingerprint_event(t.event_a)

        t.assertEqual(actual, expected)

    def test_fingerprint_event(t):
        t.ddeq.fingerprinters = []

        ret = t.ddeq._fingerprint_event(t.event_a)
        expected = DefaultFingerprintGenerator().generate(t.event_a)
        t.assertEqual(ret, expected)

        # Identical events generate the same fingerprint
        event_2 = t.event_a.copy()
        ret = t.ddeq._fingerprint_event(event_2)
        t.assertEqual(ret, expected)

    @patch("{src}.load_utilities".format(**PATH))
    def test_fingerprint_event_fingerprinters_list(t, load_utilities):
        """_fingerprint_event will attempt to generate a fingerprint from
        each ICollectorEventFingerprintGenerator it loaded,
        and return the first non-falsey value from them
        """
        fp1 = Mock(spec_set=["generate"])
        fp1.generate.return_value = None
        fp2 = Mock(spec_set=["generate"])
        fp2.generate.side_effect = lambda x: str(x)
        # fp2 returns a value, so fp3 is never called
        fp3 = Mock(spec_set=["generate"])
        fp3.generate.side_effect = lambda x: 1 / 0
        load_utilities.return_value = [fp1, fp2, fp3]
        ddeq = DeDupingEventQueue(maxlen=10)

        ret = ddeq._fingerprint_event(t.event_a)

        fp1.generate.assert_called_with(t.event_a)
        fp2.generate.assert_called_with(t.event_a)
        fp3.generate.assert_not_called()
        t.assertEqual(ret, str(t.event_a))

    def test_first_time(t):
        """given 2 events, retrun the earliest timestamp of the two
        use 'firstTime' if available, else 'rcvtime'
        """
        event1 = {"firstTime": 1, "rcvtime": 0}
        event2 = {"rcvtime": 2}

        ret = t.ddeq._first_time(event1, event2)
        t.assertEqual(ret, 1)

        event1 = {"firstTime": 3, "rcvtime": 1}
        event2 = {"rcvtime": 2}

        ret = t.ddeq._first_time(event1, event2)
        t.assertEqual(ret, 2)

    @patch("{src}.time".format(**PATH))
    def test_append_timestamp(t, time):
        """Make sure every processed event specifies the time it was queued."""
        t.ddeq.append(t.event_a)
        event = t.ddeq.popleft()

        t.assertEqual(event["rcvtime"], time.time.return_value)

    @patch("{src}.time".format(**PATH))
    def test_append_deduplication(t, time):
        """The same event cannot be added to the queue twice
        appending a duplicate event replaces the original
        """
        event1 = {"data": "some data"}
        event2 = {"data": "some data"}
        t.assertEqual(event1, event2)

        t.ddeq.append(event1)
        t.ddeq.append(event2)

        t.assertEqual(len(t.ddeq), 1)

        ret = t.ddeq.popleft()
        # The new event replaces the old one
        t.assertIs(ret, event2)
        t.assertEqual(event2["count"], 2)

    @patch("{src}.time".format(**PATH))
    def test_append_deduplicates_and_counts_events(t, time):
        time.time.side_effect = (t for t in range(100))
        t.ddeq.append({"name": "event_a"})
        t.assertEqual(list(t.ddeq), [{"rcvtime": 0, "name": "event_a"}])
        t.ddeq.append({"name": "event_a"})
        t.assertEqual(
            list(t.ddeq),
            [{"rcvtime": 1, "firstTime": 0, "count": 2, "name": "event_a"}],
        )
        t.ddeq.append({"name": "event_a"})
        t.assertEqual(
            list(t.ddeq),
            [{"rcvtime": 2, "firstTime": 0, "count": 3, "name": "event_a"}],
        )
        t.ddeq.append({"name": "event_a"})
        t.assertEqual(
            list(t.ddeq),
            [{"rcvtime": 3, "firstTime": 0, "count": 4, "name": "event_a"}],
        )

    def test_append_pops_and_returns_leftmost_if_full(t):
        t.ddeq.maxlen = 1

        t.ddeq.append(t.event_a)
        ret = t.ddeq.append(t.event_b)

        # NOTE: events are stored in a dict, key=fingerprint
        t.assertIn(t.event_b, t.ddeq)
        t.assertNotIn(t.event_a, t.ddeq)
        t.assertEqual(ret, t.event_a)

    def test_popleft(t):
        t.ddeq.append(t.event_a)
        t.ddeq.append(t.event_b)

        ret = t.ddeq.popleft()

        t.assertEqual(ret, t.event_a)

    def test_popleft_raises_IndexError(t):
        """Raises IndexError instead of KeyError, for api compatability"""
        with t.assertRaises(IndexError):
            t.ddeq.popleft()

    @patch("{src}.time".format(**PATH))
    def test_extendleft(t, time):
        """WARNING: extendleft does NOT add timestamps, as .append does
        is this behavior is intentional?
        """
        event_c = {"name": "event_c"}
        t.ddeq.append(event_c)
        t.assertEqual(list(t.ddeq), [event_c])
        events = [t.event_a, t.event_b]

        ret = t.ddeq.extendleft(events)

        t.assertEqual(ret, [])
        t.assertEqual(list(t.ddeq), [t.event_a, t.event_b, event_c])
        """
        # to validate all events get timestamps
        t.assertEqual(
            list(t.ddeq),
            [{'name': 'event_a', 'rcvtime': time.time.return_value},
             {'name': 'event_b', 'rcvtime': time.time.return_value},
             {'name': 'event_c', 'rcvtime': time.time.return_value},
            ]
        )
        """

    @patch("{src}.time".format(**PATH))
    def test_extendleft_counts_events_BUG(t, time):
        time.time.side_effect = (t for t in range(100))
        t.ddeq.extendleft([{"name": "event_a"}, {"name": "event_b"}])
        t.assertEqual(
            list(t.ddeq),
            # This should work
            # [{'rcvtime': 0, 'name': 'event_a'}]
            # current behavior
            [{"name": "event_a"}, {"name": "event_b"}],
        )
        # rcvtime is required, but is not set by extendleft
        with t.assertRaises(KeyError):
            t.ddeq.extendleft([{"name": "event_a"}, {"name": "event_b"}])
        """
        Test Breaks Here due to missing rcvtime
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_a'},
             {'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_b'}]
        )
        t.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_a'},
             {'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_b'}]
        )
        t.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_a'},
             {'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_b'}]
        )
        """

    def test_extendleft_returns_events_if_empty(t):
        ret = t.ddeq.extendleft([])
        t.assertEqual(ret, [])

    def test_extendleft_returns_extra_events_if_nearly_full(t):
        t.ddeq.maxlen = 3
        t.ddeq.extendleft([t.event_a, t.event_b])
        event_c, event_d = {"name": "event_c"}, {"name": "event_d"}
        events = [event_c, event_d]

        ret = t.ddeq.extendleft(events)

        t.assertEqual(list(t.ddeq), [event_d, t.event_a, t.event_b])
        t.assertEqual(ret, [event_c])

    def test___len__(t):
        ret = len(t.ddeq)
        t.assertEqual(ret, 0)
        t.ddeq.extendleft([t.event_a, t.event_b])
        t.assertEqual(len(t.ddeq), 2)

    def test___iter__(t):
        t.ddeq.extendleft([t.event_a, t.event_b])
        ret = list(t.ddeq)
        t.assertEqual(ret, [t.event_a, t.event_b])
