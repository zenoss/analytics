import logging

from unittest import TestCase
from mock import Mock, patch, call, MagicMock
from zope.component import adaptedBy

from ..invalidations import (
    _get_event,
    _notify_event_subscribers,
    defer,
    PrimaryPathObjectManager,
    DeletionEvent,
    UpdateEvent,
    InvalidationProcessor,
    IInvalidationProcessor,
    IHubCreatedEvent,
)
from .mock_interface import create_interface_mock


"""
These tests are currently excellent examples of tests with excessive patching
and mocking, indicating a need to refactor the code under test.
Excessive patching indicates the function has too many side-effects
Complicated Mocks indicate it reaches too deeply into external objects
"""

PATH = {"src": "Products.ZenHub.invalidations"}


class NotifyEventSubscribersTest(TestCase):
    @patch("{src}.getGlobalSiteManager".format(**PATH), autospec=True)
    @patch("{src}.providedBy".format(**PATH), autospec=True)
    @patch("{src}.giveTimeToReactor".format(**PATH), autospec=True)
    def test_notify_event_subscribers(
        t, giveTimeToReactor, providedBy, getGlobalSiteManager
    ):
        gsm = Mock(name="global_site_manager", spec_set=["adapters"])
        getGlobalSiteManager.return_value = gsm
        gsm.adapters = Mock(name="adapters", spec_set=["subscriptions"])
        subscriptions = [
            Mock(name="sub1", spec_set=[]),
            Mock(name="sub2", spec_set=[]),
        ]
        gsm.adapters.subscriptions.return_value = subscriptions

        event = Mock(name="event", spec_set=["object"])
        ret = _notify_event_subscribers(event)

        # Gets a list of subscriptions that adapt this event's interface
        gsm.adapters.subscriptions.assert_called_with(
            map(providedBy, (event.object, event)), None
        )
        # Call the subscription with the event, but wrap it in a deferred
        giveTimeToReactor.assert_has_calls(
            [
                call(subscription, event.object, event)
                for subscription in subscriptions
            ]
        )

        # InlineCallbacks return a Deferred
        t.assertIsInstance(ret, defer.Deferred)
        # Has no return value
        t.assertEqual(ret.result, None)


class GetEventTest(TestCase):
    def setUp(t):
        t.dmd = Mock(name="dmd", spec_set=["_p_jar"])
        # object must be of type PrimaryPathObjectManager or DeviceComponent
        t.obj = Mock(name="invalid type", spec_set=[])
        t.oid = "oid"
        t._p_jar = {t.oid: t.obj}
        t.dmd._p_jar = t._p_jar

    def test_get_deletion_event(t):
        obj = MagicMock(
            PrimaryPathObjectManager,
            name="primary_path_object_manager",
        )
        t.dmd._p_jar = {t.oid: obj}
        # obj.__of__(dmd).primaryAq() ensures we get the primary path
        primary_aq = obj.__of__.return_value.primaryAq
        # raising a KeyError indicates a deleted object
        primary_aq.side_effect = KeyError()

        t.assertEqual(obj, t.dmd._p_jar[t.oid])
        t.assertTrue(isinstance(obj, PrimaryPathObjectManager))

        ret = _get_event(t.dmd, obj, t.oid)
        t.assertIsInstance(ret, DeletionEvent)

    def test_get_updated_event(t):
        obj = MagicMock(
            PrimaryPathObjectManager,
            name="primary_path_object_manager",
        )
        t.dmd._p_jar = {t.oid: obj}
        obj.__of__.return_value.primaryAq.return_value = obj

        t.assertEqual(obj, t.dmd._p_jar[t.oid])
        t.assertTrue(isinstance(obj, PrimaryPathObjectManager))

        actual = _get_event(t.dmd, obj, t.oid)
        t.assertIsInstance(actual, UpdateEvent)


class InvalidationProcessorTest(TestCase):
    def setUp(t):
        logging.disable(logging.CRITICAL)
        t.patch_getGlobalSiteManager = patch(
            "{src}.getGlobalSiteManager".format(**PATH), autospec=True
        )
        t.getGlobalSiteManager = t.patch_getGlobalSiteManager.start()

        t.ip = InvalidationProcessor()
        t.ip._hub = Mock(name="zenhub", spec_set=["dmd"])
        t.ip._hub.dmd._p_jar = {}
        t.ip._hub_ready = Mock(name="_hub_ready_deferred")

    def tearDown(t):
        logging.disable(logging.NOTSET)
        t.patch_getGlobalSiteManager.stop()

    def test_init(t):
        IInvalidationProcessor.implementedBy(InvalidationProcessor)

        ip = InvalidationProcessor()

        IInvalidationProcessor.providedBy(ip)

        t.assertIsInstance(ip._hub_ready, defer.Deferred)
        # Registers its onHubCreated trigger, to wait for a HubCreated event
        gsm = t.getGlobalSiteManager.return_value
        gsm.registerHandler.assert_called_with(ip.onHubCreated)

    def test_onHubCreated(t):
        """this method gets triggered by a IHubCreatedEvent event"""
        # Is an adapter for IHubCreatedEvent type events
        t.assertEqual(
            list(adaptedBy(InvalidationProcessor.onHubCreated)),
            [IHubCreatedEvent],
        )

        IHubCreatedEventMock = create_interface_mock(IHubCreatedEvent)
        event = IHubCreatedEventMock()
        t.ip._hub_ready = Mock(spec_set=defer.Deferred)

        t.ip.onHubCreated(event)

        # _hub is set to the hub specified in the IHubCreatedEvent
        t.assertEqual(t.ip._hub, event.hub)
        # the _hub_ready deffered gets called back / triggered
        t.ip._hub_ready.callback.assert_called_with(t.ip._hub)

    @patch("{src}._get_event".format(**PATH), autospec=True)
    @patch("{src}._notify_event_subscribers".format(**PATH), autospec=True)
    def test_no_such_oids(t, notify_, get_event_):
        oids = ["oid1", "oid2", "oid3"]
        d = t.ip.processQueue(oids)
        handled, ignored = d.result

        t.assertTupleEqual((handled, ignored), (0, 0))

    @patch("{src}._get_event".format(**PATH), autospec=True)
    @patch("{src}._notify_event_subscribers".format(**PATH), autospec=True)
    def test_ignored_oids(t, notify_, get_event_):
        oids = ["oid1", "oid2", "oid3"]
        objs = [Mock(), Mock(), Mock()]
        t.ip._hub.dmd._p_jar.update(dict(zip(oids, objs)))
        d = t.ip.processQueue(oids)
        handled, ignored = d.result

        t.assertTupleEqual((handled, ignored), (0, 3))

    @patch("{src}._get_event".format(**PATH), autospec=True)
    @patch("{src}._notify_event_subscribers".format(**PATH), autospec=True)
    def test_mix_of_oids(t, notify_, get_event_):
        oids = ["oid1", "oid2", "oid3"]
        objs = [
            MagicMock(PrimaryPathObjectManager),
            Mock(),
            MagicMock(PrimaryPathObjectManager),
        ]
        t.ip._hub.dmd._p_jar.update(dict(zip(oids, objs)))
        d = t.ip.processQueue(oids)
        handled, ignored = d.result

        t.assertTupleEqual((handled, ignored), (2, 1))
