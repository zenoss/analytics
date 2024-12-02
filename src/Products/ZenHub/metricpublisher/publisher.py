##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json as _stdlib_json
import logging
import os
import sys

from collections import deque
from cookielib import CookieJar
from httplib import UNAUTHORIZED

from twisted.internet import defer, protocol, reactor
from twisted.web.client import Agent, CookieAgent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from txredis import RedisClientFactory
from zope.interface import implementer

from Products.ZenUtils.MetricServiceRequest import getPool

from .compat import json
from .utils import basic_auth_string_content, sanitized_float

defaultMetricsChannel = "metrics"
defaultMetricBufferSize = 65536
defaultPublishFrequency = 1.0
defaultRedisPort = 6379
defaultMaxOutstandingMetrics = 864000000

bufferHighWater = 4096
HTTP_BATCH = 100
INITIAL_REDIS_BATCH = 2

log = logging.getLogger("zen.publisher")


class BasePublisher(object):
    """
    Publish metrics to redis
    """

    def __init__(self, buflen, pubfreq, tagsToFilter=("internal",)):
        self._buflen = buflen
        self._pubfreq = pubfreq
        self._pubtask = None
        self._mq = deque(maxlen=buflen)
        self._tagsToFilter = tagsToFilter

    def build_metric(self, metric, value, timestamp, tags):
        # guarantee value's a float
        _value = sanitized_float(value)
        _tags = tags.copy()
        for key in self._tagsToFilter:
            if key in _tags:
                del _tags[key]
        return {
            "metric": metric,
            "value": _value,
            "timestamp": timestamp,
            "tags": _tags,
        }

    def _publish_failed(self, reason, metrics):
        """
        Push as many of the unpublished metrics as possible back into the
        message queue

        @param reason: what went wrong
        @param metrics: metrics that still need to be published
        @return: the number of metrics still in the queue. Note, this
        will stop the errback chain
        """
        log.info(
            "publishing failed: %s",
            getattr(reason, "getErrorMessage", reason.__str__)(),
        )

        open_slots = self._mq.maxlen - len(self._mq)
        self._mq.extendleft(reversed(metrics[-open_slots:]))

        return len(self._mq)

    def _reschedule_pubtask(self, scheduled):
        """
        Reschedule publish task
        @param scheduled: scheduled invocation?
        """
        if not scheduled and self._pubtask:
            self._pubtask.cancel()

        self._pubtask = reactor.callLater(self._pubfreq, self._putLater, True)

    def _put(self, scheduled):
        """
        Push the buffer of metrics to the specified Redis channel
        @param scheduled: scheduled invocation?
        """
        raise NotImplementedError("method must be overridden")

    def put(self, metric, value, timestamp, tags):
        """
        Wrap the metric, value, timestamp, and uuid in a
        JSON envelop and push it to the specified Redis
        channel

        @param metric: metric being published
        @param value: the metrics value
        @param timestamp: just that
        @param tags: dictionary of tags for the metric
        @return: a deferred that will return the number of metrics still
        in the buffer when fired
        """
        if not self._pubtask:
            self._pubtask = reactor.callLater(
                self._pubfreq, self._putLater, True
            )

        mv = self.build_metric(metric, value, timestamp, tags)
        log.debug("writing: %s", mv)

        self._mq.append(mv)

        if len(self._mq) < bufferHighWater:
            return defer.succeed(len(self._mq))
        else:
            return self._put(False)

    def _putLater(self, scheduled):
        def handleError(val):
            log.debug("Error sending metric: %s", val)

        d = self._put(scheduled=scheduled)
        d.addErrback(handleError)


class RedisListPublisher(BasePublisher):
    """
    Publish metrics to redis
    """

    def __init__(
        self,
        host="localhost",
        port=defaultRedisPort,
        buflen=defaultMetricBufferSize,
        pubfreq=defaultPublishFrequency,
        channel=defaultMetricsChannel,
        maxOutstandingMetrics=defaultMaxOutstandingMetrics,
    ):
        super(RedisListPublisher, self).__init__(buflen, pubfreq)
        self._batch_size = INITIAL_REDIS_BATCH
        self._host = host
        self._port = port
        self._channel = channel
        self._maxOutstandingMetrics = maxOutstandingMetrics
        self._redis = RedisClientFactory()
        self._flushing = False
        self._connection = reactor.connectTCP(
            self._host, self._port, self._redis
        )
        reactor.addSystemEventTrigger("before", "shutdown", self._shutdown)

    def build_metric(self, metric, value, timestamp, tags):
        """
        Override base method to work with strings instead of dicts
        """
        m = BasePublisher.build_metric(self, metric, value, timestamp, tags)
        try:
            return json.dumps(m)
        except (OverflowError, ValueError):
            # ujson can't serialize numbers larger than 64-bit signed int
            # (see https://github.com/esnme/ultrajson/issues/67).
            # Fall back to stdlib json, which does not have this limitation.
            return _stdlib_json.dumps(m)

    def _metrics_published(self, llen, metricCount, remaining=0):
        """
        Callback that logs successful publishing of metrics and
        clears the metrics buffer

        @param llen: number of metrics in Redis after publishing
        @return: the number of metrics still in the queue
        """
        log.debug("published %d metrics to redis", metricCount)
        if metricCount >= self._batch_size:
            # Batch size starts at 2, and doubles on every success,
            # up to 2**16. On failure, it drops to 2 again to allow redis
            # to recover.
            self._batch_size = min(
                2 * self._batch_size, defaultMetricBufferSize
            )

        if remaining:
            reactor.callLater(0, self._putLater, False)
        return 0

    def _get_batch_size(self):
        """
        Batch size starts at 2, and doubles on every success, up to 2**16.
        On failure, it drops to 2 again to allow redis to recover.
        """
        return self._batch_size

    def _put(self, scheduled, reschedule=True):
        """
        Push the buffer of metrics to the specified Redis channel
        @param scheduled: Whether it was a scheduled invocation
        """
        if reschedule:
            self._reschedule_pubtask(scheduled)

        if len(self._mq) == 0:
            return defer.succeed(0)

        if self._flushing:
            # still flushing keep queuing up metrics
            log.debug("metric flush to redis in progress, skipping _put")
            return defer.succeed(len(self._mq))

        if self._connection.state == "connected":
            log.debug("trying to publish %d metrics", len(self._mq))

            metrics = []
            for x in xrange(self._get_batch_size()):
                if not self._mq:
                    break
                metrics.append(self._mq.popleft())
            if not metrics:
                return defer.succeed(None)

            @defer.inlineCallbacks
            def _flush(metrics):
                if self._flushing:
                    # this should never really happen, but here as a safety
                    log.debug("rescheduling _flush")
                    num = yield reactor.deferLater(0.25, _flush, metrics)
                    defer.returnValue(num)
                log.debug(
                    "flushing %s metrics, current batch size %s",
                    len(metrics),
                    self._batch_size,
                )
                client = self._redis.client
                try:
                    self._flushing = True
                    yield client.multi()
                    yield client.lpush(self._channel, *metrics)
                    yield client.ltrim(
                        self._channel, 0, self._maxOutstandingMetrics - 1
                    )
                    result, _ = yield client.execute()
                    yield self._metrics_published(
                        result,
                        metricCount=len(metrics),
                        remaining=len(self._mq),
                    )
                    defer.returnValue(len(self._mq))
                except Exception as e:
                    # since we may be in a mutli redis command state,
                    # attempt to discard it
                    try:
                        yield client.discard()
                    except Exception:
                        pass
                    # Drop the batch size so it will ramp itself up again
                    self._batch_size = INITIAL_REDIS_BATCH
                    self._publish_failed(e, metrics=metrics)
                finally:
                    self._flushing = False

            return _flush(metrics)
        return defer.fail()

    def _shutdown(self):
        def disconnect():
            log.debug("redislistpublisher shutting down [disconnecting]")
            if self._connection.state == "connected":
                self._connection.disconnect()
            log.debug("redislistpublisher shutting down [disconnected]")

        def drainQueue(unused):
            if self._mq:
                log.debug("draining queue %s", len(self._mq))
                d = self._put(False, reschedule=False)
                d.addCallback(drainQueue)
                return d
            else:
                disconnect()

        log.debug("redislistpublisher shutting down")
        if self._connection.state != "connected":
            log.debug(
                "redislistpublisher shutting down [not connected: %s]",
                self._connection.state,
            )
        elif len(self._mq):
            log.debug(
                "redislistpublisher shutting down [publishing  metrics %s]",
                len(self._mq),
            )
            try:
                return drainQueue(None)
            except Exception as x:
                log.exception(
                    "redislistpublisher shutting down [publishing failed: %s]",
                    x,
                )
        else:
            disconnect()


class HttpPostPublisher(BasePublisher):
    """
    Publish metrics via HTTP POST
    """

    def __init__(
        self,
        username,
        password,
        url="https://localhost:8443/api/metrics/store",
        buflen=defaultMetricBufferSize,
        pubfreq=defaultPublishFrequency,
    ):
        super(HttpPostPublisher, self).__init__(buflen, pubfreq)
        self._username = username
        self._password = password
        self._needsAuth = False
        self._authenticated = False
        if self._username:
            self._needsAuth = True
        self._cookieJar = CookieJar()
        self._agent = CookieAgent(
            Agent(reactor, pool=getPool()), self._cookieJar
        )
        self._url = url
        self._agent_suffix = (
            os.path.basename(sys.argv[0].rstrip(".py"))
            if sys.argv[0]
            else "python"
        )
        reactor.addSystemEventTrigger("before", "shutdown", self._shutdown)

    def _metrics_published(self, response, llen, remaining=0):
        if response.code != 200:
            if response.code == UNAUTHORIZED:
                self._authenticated = False
                self._cookieJar.clear()
            raise IOError(
                "Expected HTTP 200, but received %d from %s"
                % (response.code, self._url)
            )

        if self._needsAuth:
            self._authenticated = True
        log.debug(
            "published %d metrics and received response: %s",
            llen,
            response.code,
        )
        finished = defer.Deferred()
        response.deliverBody(ResponseReceiver(finished))
        if remaining:
            reactor.callLater(0, self._putLater, False)
        return finished

    def _response_finished(self, result):
        # The most likely result is the HTTP response from a successful POST.
        if isinstance(result, str):
            log.debug("response was: %s", result)
        # We could be called back because _publish_failed was called before us
        elif isinstance(result, int):
            log.info("queue still contains %d metrics", result)
        # Or something strange could have happend
        else:
            log.warn("Unexpected result: %s", result)

    def _shutdown(self):
        log.debug("shutting down http [publishing %s metrics]", len(self._mq))
        if len(self._mq):
            return self._make_request()

    def _make_request(self):
        metrics = []
        for x in xrange(HTTP_BATCH):
            if not self._mq:
                break
            metrics.append(self._mq.popleft())
        if not metrics:
            return defer.succeed(None)

        serialized_metrics = json.dumps({"metrics": metrics})
        body_writer = StringProducer(serialized_metrics)

        headers = Headers(
            {
                "User-Agent": [
                    "Zenoss Metric Publisher: %s" % self._agent_suffix
                ],
                "Content-Type": ["application/json"],
            }
        )

        if self._needsAuth and not self._authenticated:
            log.info("Adding auth for metric http post %s", self._url)
            headers.addRawHeader(
                "Authorization",
                basic_auth_string_content(self._username, self._password),
            )

        log.debug("Posting %s metrics", len(metrics))
        d = self._agent.request("POST", self._url, headers, body_writer)

        d.addCallbacks(
            self._metrics_published,
            errback=self._publish_failed,
            callbackArgs=[len(metrics), len(self._mq)],
            errbackArgs=[metrics],
        )
        d.addCallbacks(
            self._response_finished,
            errback=self._publish_failed,
            errbackArgs=[metrics],
        )

        return d

    def _put(self, scheduled):
        """
        Push the buffer of metrics to the specified Redis channel
        @param scheduled: scheduled invocation?
        """
        if scheduled:
            self._reschedule_pubtask(scheduled)

        if len(self._mq) == 0:
            return defer.succeed(0)

        log.debug("trying to publish %d metrics", len(self._mq))
        return self._make_request()


@implementer(IBodyProducer)
class StringProducer(object):
    """
    Implements twisted interface for writing a string to HTTP output stream.
    """

    def __init__(self, postBody):
        self._post_body = postBody
        self.length = len(postBody)

    def startProducing(self, consumer):
        consumer.write(self._post_body)
        return defer.succeed(None)

    def stopProducing(self):
        pass

    def pauseProducing(self):
        pass

    def resumeProducing(self):
        pass


class ResponseReceiver(protocol.Protocol):
    """
    Captures HTTP response from POST
    """

    def __init__(self, deferred):
        self._buffer = ""
        self._deferred = deferred

    def dataReceived(self, data):
        self._buffer += data

    def connectionLost(self, reason):
        log.debug("connection closed")
        self._deferred.callback(self._buffer)
