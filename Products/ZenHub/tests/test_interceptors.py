##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import Mock, MagicMock, patch

from Products.ZenHub.interceptors import (
    WorkerInterceptor,
    pb,
    pickle,
    defer,
)


PATH = {'interceptors': 'Products.ZenHub.interceptors'}


class WorkerInterceptorTest(TestCase):

    def setUp(self):
        self.cap_args = [
            'tuple',
            ['list',
                ['dictionary',
                    ['monitor', 'localhost'],
                    ['component', 'zenstatus'],
                    ['agent', 'zenstatus'],
                    ['manager', '550b82acdec1'],
                    ['timeout', 900],
                    ['device', 'localhost'],
                    ['eventClass', '/Heartbeat']]]]

        self.cap_kw = ['dictionary']

        self.service = MagicMock(name='service')
        self.service.__class__ = (
            'Products.ZenHub.services.EventService.EventService'
        )
        self.service.__str__.return_value = 'service.__str__'
        self.zenhub = Mock(name='zenhub instance')
        self.zenhub.deferToWorker.return_value = 'deferred'
        self.wi = WorkerInterceptor(zenhub=self.zenhub, service=self.service)
        self.broker = Mock(name='pb.Broker', spec=pb.Broker)

    def test_remoteMessageRecieved(self):
        state = self.wi.remoteMessageRecieved(
            broker=self.broker,  # twisted.spread.pb.Broke
            message='applyDataMaps',
            args=self.cap_args,
            kw=self.cap_kw,
        )

        # the event has been sent the ZenHub Workers
        svc_name = self.wi.service_name
        chunked_args = self.wi.chunk_args(self.cap_args, self.cap_kw)
        self.zenhub.deferToWorker.assert_called_with(
            svc_name,
            self.service.instance,
            'applyDataMaps',
            chunked_args
        )
        # remoteMessageRecieved returns a Deferred
        self.assertIsInstance(state, defer.Deferred)
        # the result of state is pb.Broker.serialize()
        self.assertEqual(state.result, self.broker.serialize.return_value)
        # pb.Broker.serialize was called with expected args
        self.broker.serialize.assert_called_with(
            self.zenhub.deferToWorker.return_value,
            self.wi.perspective
        )

    def test_remoteMessageRecieved_sendEvent(self):
        state = self.wi.remoteMessageRecieved(
            broker=self.broker,  # twisted.spread.pb.Broke
            message='sendEvent',
            args=self.cap_args,
            kw=self.cap_kw,
        )

        self.assertIsInstance(state, defer.Deferred)
        self.broker.unserialize.assert_called_with(self.cap_args)
        self.zenhub.zem.sendEvent.assert_called_with(
            self.broker.unserialize.return_value
        )

    def test_remoteMessageRecieved_sendEvents(self):
        state = self.wi.remoteMessageRecieved(
            broker=self.broker,  # twisted.spread.pb.Broke
            message='sendEvents',
            args=self.cap_args,
            kw=self.cap_kw,
        )

        self.assertIsInstance(state, defer.Deferred)
        self.broker.unserialize.assert_called_with(self.cap_args)
        self.zenhub.zem.sendEvents.assert_called_with(
            self.broker.unserialize.return_value
        )

    def test_service_name(self):
        self.assertEqual(
            self.wi.service_name, 'Products.ZenHub.services.EventService'
        )

    def test_chunk_args(self):
        chunked_args = self.wi.chunk_args(self.cap_args, self.cap_kw)
        self.assertEqual(
            pickle.loads(''.join(chunked_args)),
            (self.cap_args, self.cap_kw)
        )
        self.assertEqual(
            chunked_args,
            [pickle.dumps(
                (self.cap_args, self.cap_kw),
                pickle.HIGHEST_PROTOCOL
            )]
        )

    def test_chunk_args_long(self):
        # build args that will be more than the 102400 char limit once pickled
        args = ['10 chr str' for _ in range(100000)]
        kwargs = {'kw': 'args', }
        chunked_args = self.wi.chunk_args(args, kwargs)

        # join the chunked args back to a sting, and unpickle them.
        self.assertEqual(
            pickle.loads(''.join(chunked_args)),
            (args, kwargs)
        )

    def test_mark_send_event_timer(self):
        self.wi._eventsSent = Mock(
            name='_eventsSent', spec=self.wi._eventsSent
        )
        self.wi.mark_send_event_timer(None, None)
        self.wi._eventsSent.mark.assert_called_with()

    def test_mark_send_events_timer(self):
        self.wi._eventsSent = Mock(
            name='_eventsSent', spec=self.wi._eventsSent
        )
        events = ['a', 'b']
        self.wi.mark_send_events_timer(events, None)
        self.wi._eventsSent.mark.assert_called_with(len(events))

    @patch('{interceptors}.time'.format(**PATH), name='time', autospec=True)
    def test_mark_apply_datamaps_timer(self, mtime):
        self.wi._admTimer = Mock(name='_eventsSent', spec=self.wi._admTimer)
        mtime.return_value = 300
        start = 100
        self.wi.mark_apply_datamaps_timer(None, start)
        self.wi._admTimer.update.assert_called_with(
            (mtime() - start) * 1000
        )
