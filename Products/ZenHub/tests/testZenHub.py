##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
import Globals

from Products.ZenTestCase.BaseTestCase import ZenossTestCaseLayer, BaseTestCase
from Products.ZenUtils.Driver import drive

# Import from zenhub before importing twisted.internet.reactor
from Products.ZenHub.zenhub import ZenHub
from Products.ZenHub.PBDaemon import RemoteException, RemoteConflictError

from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.cred import credentials
from twisted.spread import pb
import sys
import os

from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher
from Products.ZenMessaging.queuemessaging.publisher import DummyQueuePublisher, EventPublisher

import Products.ZenHub.zenhub

count = 0
def stop(ignored=None, connector=None):
    if isinstance(ignored, Exception):
        raise ignored
    if reactor.running:
        if getattr(reactor, 'threadpool', None) is not None:
            reactor.threadpool.stop()
            reactor.threadpool = None
        reactor.crash()
    if connector:
        connector.disconnect()

class TestClient(pb.Referenceable):

    success = False
    svc = 'Products.ZenHub.tests.TestService'

    def __init__(self, tester, port):
        self.tester = tester
        factory = pb.PBClientFactory()
        self.connector = reactor.connectTCP("localhost", port, factory)
        creds = credentials.UsernamePassword("admin", "zenoss")
        d = factory.login(creds, client=self)
        d.addCallback(self.connected)
        d.addErrback(self.bad)

    def connected(self, perspective):
        d = perspective.callRemote('getService', self.svc, 'localhost', self)
        d.addCallback(self.test)
        d.addErrback(self.bad)

    def bad(self, reason):
        stop(connector=self.connector)
        self.tester.fail('error: '+str(reason.value))

    def test(self, service):
        def Test(driver):
            data = ('Some Data', 17)
            yield service.callRemote('echo', data)
            self.tester.assertEqual(driver.next(), data)
            self.success = True
        drive(Test).addBoth(stop, connector=self.connector)

class SendEventClient(TestClient):
    svc = 'EventService'

    def test(self, service):
        def Test(driver):

            evt = dict(device='localhost',
                       severity='5',
                       summary='This is a test message')
            yield service.callRemote('sendEvents', [evt])
            self.tester.assertEqual(driver.next(), 1)
            self.success = True
        drive(Test).addBoth(stop, connector=self.connector)


class RaiseExceptionClient(TestClient):
    exception = None

    def complete( self, result):
        stop( self.connector)
        self.tester.assertIsInstance( result, Failure)
        self.exception = result.value

    def test(self, service):
        def Test(driver):
            yield service.callRemote('raiseException', "an exception message")
        drive(Test).addBoth(self.complete)

class RaiseConflictErrorClient(TestClient):
    exception = None

    def complete( self, result):
        stop( self.connector)
        self.tester.assertIsInstance( result, Failure)
        self.exception = result.value

    def test(self, service):
        def Test(driver):
            yield service.callRemote('raiseConflictError', "an error message")
        drive(Test).addBoth(self.complete)

class TestZenHub(BaseTestCase):

    layer = ZenossTestCaseLayer

    base = 7000
    xbase = 8000

    def afterSetUp(self):
        super(TestZenHub, self).afterSetUp()
        global count
        count += 1
        base = self.base + count
        xbase = self.xbase + count
        self.before, sys.argv = sys.argv, ['run',
                                           '--pbport=%d' % base,
                                           '--xmlrpcport=%d' % xbase,
                                           '--workers=0']
        self.zenhub = ZenHub()
        from zope.component import getGlobalSiteManager
        # The call to zenhub above overrides the queue so we need to
        # re-override it
        gsm = getGlobalSiteManager()
        queue = DummyQueuePublisher()
        gsm.registerUtility(queue, IQueuePublisher)

    def beforeTearDown(self):
        sys.argv = self.before
        super(TestZenHub, self).beforeTearDown()

    def testPbRegistration(self):
        from twisted.spread.jelly import unjellyableRegistry
        self.assertTrue(unjellyableRegistry.has_key('DataMaps.ObjectMap'))
        self.assertTrue(unjellyableRegistry.has_key('Products.DataCollector.plugins.DataMaps.ObjectMap'))

    def testGetService(self):
        client = TestClient(self, self.base + count)
        self.assertFalse(client.success)
        self.zenhub.main()
        self.assertTrue(client.success)

    def testSendEvent(self):
        EventPublisher._publisher = DummyQueuePublisher()
        client = SendEventClient(self, self.base + count)
        self.assertFalse(client.success)
        self.zenhub.main()
        self.assertTrue(client.success)

    def testRaiseRemoteException(self):
        client = RaiseExceptionClient(self, self.base + count)
        self.assertIs( client.exception, None)
        self.zenhub.main()
        self.assertIsInstance( client.exception, RemoteException)
        self.assertIn( "an exception message", str(client.exception))
        self.assertIsNotNone( client.exception.traceback)

    def testRaiseRemoteConflictError(self):
        client = RaiseConflictErrorClient(self, self.base + count)
        self.assertIs( client.exception, None)
        self.zenhub.main()
        self.assertIsInstance( client.exception, RemoteConflictError)
        self.assertIn( "an error message", str(client.exception))
        self.assertIsNotNone( client.exception.traceback)

class Publisher(object):
    def __init__(self):
        self.queue = []

    def put(self, *args):
        self.queue.append( args)


class TestMetricWriter(BaseTestCase):
    def setUp(self):
        os.environ["CONTROLPLANE"] = "0"
        self.publisher = Publisher()
        self.publisher_cache = Products.ZenHub.zenhub.publisher
        self.redispublisher_cache = Products.ZenHub.zenhub.redisPublisher
        Products.ZenHub.zenhub.publisher = lambda u,p,url: self.publisher
        Products.ZenHub.zenhub.redisPublisher = lambda:self.publisher
        self.metric_writer = Products.ZenHub.zenhub.metricWriter()

    def tearDown(self):
        Products.ZenHub.zenhub.publisher = self.publisher_cache
        Products.ZenHub.zenhub.redisPublisher = self.redispublisher_cache

    def testWriteMetric(self):
        metric = [ "name", 0.0, "now", {}]
        self.metric_writer.write_metric( *metric)
        self.assertEquals( [tuple(metric)], self.publisher.queue)

class TestInternalMetricWriter(BaseTestCase):
    def setUp(self):
        os.environ["CONTROLPLANE"] = "1"
        os.environ["CONTROLPLANE_CONSUMER_URL"] = "1"
        self.publisher = Publisher()
        self.internal_publisher = Publisher()
        self.publisher_cache = Products.ZenHub.zenhub.publisher
        self.redispublisher_cache = Products.ZenHub.zenhub.redisPublisher
        Products.ZenHub.zenhub.publisher = lambda u,p,url:self.internal_publisher
        Products.ZenHub.zenhub.redisPublisher = lambda:self.publisher
        self.metric_writer = Products.ZenHub.zenhub.metricWriter()

    def testWriteInternalMetric(self):
        metric = ["name", 0.0, "now", {}]
        internal_metric = ["name", 0.0, "now", {"internal":True}]
        self.metric_writer.write_metric( *metric)
        self.metric_writer.write_metric( *internal_metric)
        self.assertEquals( [tuple(metric), tuple(internal_metric)], self.internal_publisher.queue)
        self.assertEquals( [tuple(metric), tuple(internal_metric)], self.publisher.queue)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestZenHub))
    suite.addTest(unittest.makeSuite(TestMetricWriter))
    suite.addTest(unittest.makeSuite(TestInternalMetricWriter))
    return suite
