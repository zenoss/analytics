##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from unittest import TestCase
from mock import Mock, MagicMock, create_autospec, patch
from zope.interface.verify import verifyObject

from Products.ZenHub.metricpublisher.publisher import (
    BasePublisher,
    basic_auth_string_content,
    CookieAgent,
    CookieJar,
    defaultMetricBufferSize,
    defaultPublishFrequency,
    defer,
    deque,
    Headers,
    HttpPostPublisher,
    IBodyProducer,
    INITIAL_REDIS_BATCH,
    json,
    os,
    RedisClientFactory,
    RedisListPublisher,
    ResponseReceiver,
    StringProducer,
    sys,
    UNAUTHORIZED,
)


METRIC = "testMetricName"
BUFFER_LEN = 10
PUBLISHER_FREQ = 10
SCHEDULED = True

PATH = {"src": "Products.ZenHub.metricpublisher.publisher"}


class DisableLoggingLayer(object):
    @classmethod
    def setUp(self):
        logging.disable(logging.CRITICAL)


class BasePublisherTest(TestCase):

    layer = DisableLoggingLayer

    def setUp(self):
        self.pub = BasePublisher(BUFFER_LEN, PUBLISHER_FREQ)
        self.metric = {"metric": "m", "value": 1.0, "timestamp": 1, "tags": {}}
        self.metric_builded = [
            str(
                {
                    "timestamp": 1535460634.26479,
                    "metric": "eventQueueLength",
                    "value": 0.0,
                    "tags": {
                        "instance": "0",
                        "daemon": "zenpython",
                        "monitor": "localhost",
                        "metricType": "GAUGE",
                        "tenantId": "b0e4t72hrole5z1xv88djc1hb",
                    },
                }
            )
        ]

    def test___init__(self):
        metric_queue = deque(maxlen=BUFFER_LEN)
        tagsToFilter = ("internal",)
        publisher = BasePublisher(BUFFER_LEN, PUBLISHER_FREQ)
        self.assertEqual(publisher._buflen, BUFFER_LEN)
        self.assertEqual(publisher._pubfreq, PUBLISHER_FREQ)
        self.assertEqual(publisher._pubtask, None)
        self.assertEqual(publisher._mq, metric_queue)
        self.assertEqual(publisher._tagsToFilter, tagsToFilter)

    def test_build_metric(self):
        self.assertEqual(self.metric, self.pub.build_metric("m", 1.0, 1, {}))
        self.assertEqual(self.metric, self.pub.build_metric("m", "1.0", 1, {}))

    def test__publish_failed(self):
        PublishError = Mock(Exception, name="PublishError", autospec=True)
        result = self.pub._publish_failed(
            reason=PublishError, metrics=self.metric_builded
        )
        self.assertEqual(result, len(self.metric_builded))
        self.assertEqual(len(self.pub._mq), len(self.metric_builded))

    def test__reschedule_pubtask(self):
        self.pub._reschedule_pubtask(scheduled=True)
        # check if we created new task
        self.assertTrue(self.pub._pubtask)

    def test__reschedule_pubtask_cancel(self):
        self.pub._reschedule_pubtask(scheduled=True)
        canceled_task = self.pub._pubtask
        # check if we canceled the previous task
        self.pub._reschedule_pubtask(scheduled=False)
        cancel_flag = 1
        self.assertEqual(canceled_task.cancelled, cancel_flag)

    def test__put_not_impl(self):
        with self.assertRaises(NotImplementedError):
            self.pub._put(scheduled=False)

    def test_put(self):
        self.pub.build_metric = create_autospec(
            self.pub.build_metric, return_value=self.metric_builded
        )
        result = self.pub.put(METRIC, value=1, timestamp=123.4, tags={})
        self.assertIsInstance(result, defer.Deferred)
        self.assertEqual(len(self.pub._mq), len(self.metric_builded))

    def test__putLater(self):
        self.pub._put = create_autospec(self.pub._put)
        self.pub._putLater(scheduled=True)
        self.pub._put.assert_called_once_with(scheduled=True)


class RedisPublisherTest(TestCase):

    layer = DisableLoggingLayer

    def setUp(self):
        self.pub = RedisListPublisher()
        self.metric = json.dumps(
            {"metric": "m", "value": 3.3, "timestamp": 1, "tags": {}}
        )

    @patch(
        "Products.ZenHub.metricpublisher.publisher.reactor",
        autospec=True,
        spec_set=True,
    )
    def test___init__(self, reactor):
        redis_host = "10.111.23.23"
        redis_port = 6379
        redis_channel = "default"
        redis_max_metrics = 150000
        pub = RedisListPublisher(
            host=redis_host,
            port=redis_port,
            buflen=BUFFER_LEN,
            pubfreq=PUBLISHER_FREQ,
            channel=redis_channel,
            maxOutstandingMetrics=redis_max_metrics,
        )
        self.assertEqual(pub._batch_size, INITIAL_REDIS_BATCH)
        self.assertEqual(pub._host, redis_host)
        self.assertEqual(pub._port, redis_port)
        self.assertEqual(pub._channel, redis_channel)
        self.assertEqual(pub._maxOutstandingMetrics, redis_max_metrics)
        self.assertIsInstance(pub._redis, RedisClientFactory)
        # flashing should be false in the begining
        self.assertFalse(pub._flushing)
        reactor.connectTCP.assert_called_with(
            redis_host, pub._port, pub._redis
        )

    def test_build_metric(self):
        metric = self.pub.build_metric(
            metric="m", value=3.3, timestamp=1, tags={}
        )
        self.assertEqual(metric, self.metric)
        self.assertIsInstance(metric, str)

    @patch(
        "Products.ZenHub.metricpublisher.publisher.reactor",
        autospec=True,
        spec_set=True,
    )
    def test__metrics_published(self, reactor):
        # params llen and metricCount are probably the same
        # this should double the `_batch_size` in next publish iteration
        self.pub._metrics_published(
            llen=INITIAL_REDIS_BATCH,
            metricCount=INITIAL_REDIS_BATCH,
            remaining=0,
        )
        double_size = INITIAL_REDIS_BATCH * 2
        self.assertEqual(self.pub._batch_size, double_size)
        self.pub._batch_size = defaultMetricBufferSize
        self.pub._metrics_published(
            llen=INITIAL_REDIS_BATCH,
            metricCount=defaultMetricBufferSize * 2,
            remaining=10,
        )
        reactor.callLater.assert_called_with(0, self.pub._putLater, False)
        self.assertEqual(self.pub._batch_size, defaultMetricBufferSize)

    def test__get_batch_size(self):
        self.assertEqual(self.pub._batch_size, INITIAL_REDIS_BATCH)

    def test_put_default(self):
        self.pub.put("m", "3.3", 1, {})
        self.pub.put("m", 3.3, 1, {})
        # we put two metrics inside
        self.assertEqual(2, len(self.pub._mq))
        self.assertEqual(self.metric, self.pub._mq.pop())
        self.assertEqual(self.metric, self.pub._mq.pop())

    def test__put(self):
        self.pub._reschedule_pubtask = create_autospec(
            self.pub._reschedule_pubtask, spec_set=True
        )
        self.pub._metrics_published = create_autospec(
            self.pub._metrics_published, spec_set=True
        )
        self.pub._connection = create_autospec(self.pub._connection)
        self.pub._connection.state = "connected"
        self.pub._redis.client = create_autospec(self.pub._redis.client)
        self.pub._redis.client.execute.return_value = (1, 1)
        self.pub.put("m", "0", 1, {})
        result = self.pub._put(scheduled=SCHEDULED, reschedule=True)
        self.assertIsInstance(result, defer.Deferred)
        self.assertEqual(len(self.pub._mq), 0)
        self.pub._reschedule_pubtask.assert_called_once_with(
            scheduled=SCHEDULED
        )
        self.pub._metrics_published.assert_called_once_with(1, 1, 0)

    def test__put_fail(self):
        # check the put when there is Exception in writing to Redis
        self.pub._publish_failed = create_autospec(
            self.pub._publish_failed, spec_set=True
        )
        self.pub._connection = create_autospec(self.pub._connection)
        self.pub._connection.state = "connected"
        self.pub._redis.client = create_autospec(
            self.pub._redis.client, spec_set=True
        )
        exception_instace = Exception("Boom")
        self.pub._redis.client.execute.side_effect = exception_instace
        self.pub.put("m", "0", 1, {})
        # it will fall into Exception when unpacking client.execute()
        # so the state of the publisher should be restored
        self.pub._put(scheduled=SCHEDULED, reschedule=True)
        self.assertEqual(self.pub._batch_size, INITIAL_REDIS_BATCH)
        self.pub._publish_failed.assert_called_once_with(
            exception_instace,
            metrics=['{"timestamp":1,"metric":"m","value":0.0,"tags":{}}'],
        )

    @patch(
        "Products.ZenHub.metricpublisher.publisher.defer.Deferred",
        autospec=True,
    )
    def test__shutdown(self, Deferred):
        self.pub._connection = create_autospec(self.pub._connection)
        self.pub._connection.state = "connected"
        return_val = defer.Deferred
        self.pub._put = create_autospec(
            self.pub._put, spec_set=True, return_value=return_val
        )
        self.pub.put("m", "0", 1, {})
        result = self.pub._shutdown()
        # run _shutdown once more we wont have any metrics in _mq
        # so diconnect will be called
        self.pub._mq.pop()
        self.pub._shutdown()
        self.assertEqual(result, return_val)
        self.pub._put.assert_called_once_with(
            scheduled=False, reschedule=False
        )
        self.pub._connection.disconnect.assert_called_once_with()


class HttpPostPublisherTest(TestCase):

    layer = DisableLoggingLayer

    def setUp(self):
        self.username = "root"
        self.password = "root"
        self.url = "https://localhost"
        if sys.argv[0]:
            self._agent_suffix = os.path.basename(sys.argv[0].rstrip(".py"))
        else:
            self._agent_suffix = "python"
        self.pub = HttpPostPublisher(
            username=self.username, password=self.password, url=self.url
        )

    def test___init__(self):
        self.assertEqual(self.pub._buflen, defaultMetricBufferSize)
        self.assertEqual(self.pub._pubfreq, defaultPublishFrequency)
        self.assertEqual(self.pub._username, self.username)
        self.assertEqual(self.pub._password, self.password)
        self.assertEqual(self.pub._url, self.url)
        self.assertEqual(self.pub._needsAuth, True)
        self.assertEqual(self.pub._authenticated, False)
        self.assertIsInstance(self.pub._cookieJar, CookieJar)
        self.assertIsInstance(self.pub._agent, CookieAgent)
        self.assertEqual(self.pub._agent_suffix, self._agent_suffix)

    def test__metrics_published_fail(self):
        response = Mock(name="Resonse", spec_set=["code"], code=UNAUTHORIZED)
        self.pub._cookieJar = create_autospec(
            self.pub._cookieJar, spec_set=True
        )
        self.pub._authenticated = True
        with self.assertRaises(IOError):
            self.pub._metrics_published(response, llen=10, remaining=10)
        self.assertEqual(self.pub._authenticated, False)
        self.pub._cookieJar.clear.assert_called_with()

    @patch(
        "Products.ZenHub.metricpublisher.publisher.ResponseReceiver",
        autospec=True,
        spec_set=True,
    )
    def test__metrics_published(self, ResponseReceiver):
        response = Mock(
            name="Response", spec_set=["code", "deliverBody"], code=200
        )
        d = defer.Deferred()
        self.pub._metrics_published(response, llen=10, remaining=10)
        # since we got 200 we were successfully authenticated
        self.assertEqual(self.pub._authenticated, True)
        response.deliverBody.assert_called_with(ResponseReceiver(d))

    def test__shutdown(self):
        self.pub._make_request = create_autospec(self.pub._make_request)
        self.pub.put("m", "1.0", 1, {})
        self.pub._shutdown()
        self.pub._make_request.assert_called_with()

    @patch(
        "Products.ZenHub.metricpublisher.publisher.StringProducer",
        autospec=True,
        spec_set=True,
    )
    def test__make_request(self, StringProducer):
        d = create_autospec(defer.Deferred, spec_set=True)
        self.pub._agent.request = create_autospec(
            self.pub._agent.request, return_value=d
        )
        metrics = [{"metric": "m", "value": 1.0, "timestamp": 1, "tags": {}}]
        headers = Headers(
            {
                "User-Agent": [
                    "Zenoss Metric Publisher: {}".format(
                        self.pub._agent_suffix
                    )
                ],
                "Content-Type": ["application/json"],
            }
        )
        headers.addRawHeader(
            "Authorization",
            basic_auth_string_content(self.pub._username, self.pub._password),
        )
        body_writer = StringProducer(json.dumps({"metrics": metrics}))
        self.pub.put("m", "1.0", 1, {})
        self.pub._make_request()
        self.pub._agent.request.assert_called_with(
            "POST", self.pub._url, headers, body_writer
        )
        d.addCallbacks.assert_any_call(
            self.pub._metrics_published,
            errback=self.pub._publish_failed,
            callbackArgs=[len(metrics), len(self.pub._mq)],
            errbackArgs=[metrics],
        )
        d.addCallbacks.assert_any_call(
            self.pub._response_finished,
            errback=self.pub._publish_failed,
            errbackArgs=[metrics],
        )

    @patch(
        "Products.ZenHub.metricpublisher.publisher.defer",
        autospec=True,
        spec_set=True,
    )
    def test__put(self, defer):
        self.pub._reschedule_pubtask = create_autospec(
            self.pub._reschedule_pubtask, spec_set=True
        )
        self.pub._make_request = create_autospec(
            self.pub._make_request, spec_set=True
        )
        result = self.pub._put(scheduled=SCHEDULED)
        self.assertEqual(result, defer.succeed.return_value)
        self.pub._reschedule_pubtask.assert_called_with(scheduled=SCHEDULED)
        self.pub.put("m", "1.0", 1, {})
        self.pub._put(scheduled=SCHEDULED)
        self.pub._make_request.assert_called_with()


class StringProducerTest(TestCase):
    def setUp(self):
        self.body_data = ""
        self.str_producer = StringProducer(postBody=self.body_data)

    def test___init__(self):
        self.assertTrue(IBodyProducer.implementedBy(StringProducer))
        self.assertTrue(IBodyProducer.providedBy(self.str_producer))
        verifyObject(IBodyProducer, self.str_producer)
        self.assertEqual(self.str_producer._post_body, self.body_data)
        self.assertEqual(self.str_producer.length, len(self.body_data))

    @patch(
        "Products.ZenHub.metricpublisher.publisher.defer",
        autospec=True,
        spec_set=True,
    )
    def test_startProducing(self, defer):
        consumer = MagicMock()
        result = self.str_producer.startProducing(consumer=consumer)
        consumer.write.asser_called_with(self.str_producer._post_body)
        self.assertEqual(result, defer.succeed.return_value)


class ResponseReceiverTest(TestCase):
    def setUp(self):
        self.deferred = MagicMock()
        self.res_receiver = ResponseReceiver(self.deferred)

    def test___init__(self):
        self.assertEqual(self.res_receiver._buffer, "")
        self.assertEqual(self.res_receiver._deferred, self.deferred)

    def test_dataReceived(self):
        data = "some data"
        self.res_receiver.dataReceived(data)
        self.assertEqual(self.res_receiver._buffer, data)

    def test_connectionLost(self):
        # reason is not used in method but is in it signature
        self.res_receiver.connectionLost(reason="some reason")
        self.res_receiver._deferred.callback.asser_called_with(
            self.res_receiver._buffer
        )
