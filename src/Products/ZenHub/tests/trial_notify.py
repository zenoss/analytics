##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Twisted Trial unittests for the ZenHub/notify.py module. Run this
test with

  $ trial $ZENHOME/Products/ZenHub/tests/trial_notify.py

or with more detailed logging...

  $ DEBUG=1 trial $ZENHOME/Products/ZenHub/tests/trial_notify.py

"""

import os
import logging

from twisted.trial import unittest
from twisted.internet import reactor, defer, base
from twisted.python import failure

from Products.ZenHub import notify

_DEBUG = os.environ.get("DEBUG", False)
if _DEBUG:
    base.DelayedCall.debug = True
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO
logging.basicConfig(level=logging_level)


class IgnoreThisError(Exception):
    pass


class Service(object):
    def __init__(self, name):
        self.name = name

    def notifyAll(self, device):
        logging.debug(
            "Service{name: %s}.notifyAll(device=%s)" % (self.name, device)
        )


class DeviceClass(object):
    def __init__(self, uid, subdevices=[]):
        self.uid = uid
        self.subdevices = subdevices

    def getPrimaryId(self):
        return self.uid

    def getSubDevicesGen(self):
        return iter(self.subdevices)

    def __repr__(self):
        return self.uid


class BatchNotifierTestCase(unittest.TestCase):
    def setUp(self):
        logging.debug("\nBatchNotifierTestCase.setUp")
        self.notifier = notify.BatchNotifier()

    def tearDown(self):
        logging.debug("BatchNotifierTestCase.tearDown")
        self.notifier = None

    def test_twisted_trial(self):
        logging.debug("BatchNotifierTestCase.test_twisted_trial")
        d = defer.Deferred()
        reactor.callLater(0.05, d.callback, None)
        return d

    def test_simple(self):
        self.assertNot(self.notifier._queue)
        self.do_notify_subdevices("test_device_class_01", 1)
        return self.notifier._queue[0].d

    def test_multiple_device_classes(self):
        self.assertNot(self.notifier._queue)
        self.do_notify_subdevices("test_device_class_01", 1)
        d1 = self.notifier._queue[0].d
        self.do_notify_subdevices("test_device_class_02", 2)
        d2 = self.notifier._queue[0].d
        self.assertNotEqual(d1, d2)
        self.do_notify_subdevices("test_device_class_01", 2)
        d3 = self.notifier._queue[0].d
        self.assertEqual(d2, d3)
        return d2

    def do_notify_subdevices(
        self,
        device_class_uid,
        expected_queue_len,
        subdevices=["foo_device", "bar_device"],
    ):
        device_class = DeviceClass(device_class_uid, subdevices)
        for s in [Service("quux_service"), Service("blah_service")]:
            self.notifier.notify_subdevices(device_class, s.name, s.notifyAll)
        self.assertEqual(expected_queue_len, len(self.notifier._queue))

    def test_errback(self):
        try:
            raise IgnoreThisError("just testing the errback")
        except IgnoreThisError:
            self.notifier._errback(failure.Failure())
