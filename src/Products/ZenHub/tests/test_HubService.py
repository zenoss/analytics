from unittest import TestCase
from mock import Mock, patch, create_autospec, call

from Products.ZenHub.HubService import HubService, logging, socket, pb


PATH = {"HubService": "Products.ZenHub.HubService"}


class TestHubService(TestCase):
    def setUp(self):
        self.dmd = Mock(name="dmd")
        self.instance = Mock(name="instance")

        self.hub_service = HubService(self.dmd, self.instance)

    def test_init(self):
        self.assertIsInstance(self.hub_service, pb.Referenceable)

        # Validate attributes created by __init__
        self.assertEqual(
            self.hub_service.log, logging.getLogger("zen.hub.hubservice")
        )
        self.assertEqual(self.hub_service.fqdn, socket.getfqdn())
        self.assertEqual(self.hub_service.dmd, self.dmd)
        self.assertEqual(self.hub_service.zem, self.dmd.ZenEventManager)
        self.assertEqual(self.hub_service.instance, self.instance)
        self.assertEqual(self.hub_service.listeners, [])
        self.assertEqual(self.hub_service.listenerOptions, {})
        self.assertEqual(self.hub_service.callTime, 0)

    def test_getPerformanceMonitor(self):
        out = self.hub_service.getPerformanceMonitor()

        self.dmd.Monitors.getPerformanceMonitor.assert_called_with(
            self.instance
        )
        self.assertEqual(
            out, self.dmd.Monitors.getPerformanceMonitor.return_value
        )

    @patch(
        "{HubService}.pb.Referenceable.remoteMessageReceived".format(**PATH),
        autospec=True,
        spec_set=True,
    )
    @patch(
        "{HubService}.time.time".format(**PATH), autospec=True, spec_set=True
    )
    def test_remoteMessageReceived(self, time, remoteMessageReceived):
        Broker = Mock(name="pb.Broker")
        broker = Broker()
        message = "message"
        args = []
        kw = {}
        times = [3, 5]
        time.side_effect = times

        out = self.hub_service.remoteMessageReceived(broker, message, args, kw)

        pb.Referenceable.remoteMessageReceived.assert_called_with(
            self.hub_service, broker, message, args, kw
        )
        self.assertEqual(
            out, pb.Referenceable.remoteMessageReceived.return_value
        )
        self.assertEqual(self.hub_service.callTime, times[1] - times[0])

    def test_update_is_deprecated(self):
        self.hub_service.update("object")
        # Deprecated function with no output or side-effects

    def test_deleted_is_deprecated(self):
        self.hub_service.deleted("object")
        # Deprecated function with no output or side-effects

    def test_name(self):
        out = self.hub_service.name()
        self.assertEqual(out, self.hub_service.__class__.__name__)

    def test_addListener(self):
        remote = Mock(name="remote")
        options = Mock(name="options")

        self.hub_service.addListener(remote, options=options)

        remote.notifyOnDisconnect.assert_called_with(
            self.hub_service.removeListener
        )
        self.assertIn(remote, self.hub_service.listeners)
        self.assertEqual(self.hub_service.listenerOptions[remote], options)

    def test_removeListener(self):
        listener = Mock(name="listener")
        options = Mock(name="options")
        self.hub_service.listeners = [listener]
        self.hub_service.listenerOptions[listener] = options

        self.hub_service.removeListener(listener)

        self.assertNotIn(listener, self.hub_service.listeners)
        self.assertNotIn(listener, self.hub_service.listenerOptions.keys())

    def test_sendEvents(self):
        events = ["evt1", "evt2", "evt3"]
        self.hub_service.sendEvent = create_autospec(
            self.hub_service.sendEvent, name="HubService.sendEvent"
        )

        self.hub_service.sendEvents(events)
        self.hub_service.sendEvent.assert_has_calls([call(x) for x in events])

    @patch("Products.ZenEvents.Event.Event", autospec=True, spec_set=True)
    def test_sendEvent(self, Event):
        # This should accept an Products.ZenEvents.Event.Event object, but
        # currently only accepts a dict, which is converted to an Event later
        event = {}
        kw = {"kwarg_a": "kwarg_1", "kwarg_b": "kwarg_2"}

        self.hub_service.sendEvent(event, **kw)

        sent_event = {
            "agent": "zenhub",
            "monitor": self.hub_service.instance,
            "manager": self.hub_service.fqdn,
            "kwarg_a": kw["kwarg_a"],
            "kwarg_b": kw["kwarg_b"],
        }

        self.hub_service.zem.sendEvent.assert_called_with(sent_event)
