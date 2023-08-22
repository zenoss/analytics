##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import zope.component
import zope.interface

from cryptography.fernet import Fernet
from twisted.internet import defer

from Products.ZenCollector.config import ConfigurationProxy
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences

from Products.ZenTestCase.BaseTestCase import BaseTestCase


class MyCollector(object):
    zope.interface.implements(ICollector)

    class MyConfigServiceProxy(object):
        def remote_propertyItems(self):
            return defer.succeed({"name": "foobar", "foobar": "abcxyz"})

        def remote_getThresholdClasses(self):
            return defer.succeed(["Products.ZenModel.FooBarThreshold"])

        def remote_getCollectorThresholds(self):
            return defer.succeed(["yabba dabba do", "ho ho hum"])

        def remote_getDeviceConfigs(self, devices=[]):
            return defer.succeed(["hmm", "foo", "bar"])

        def remote_getEncryptionKey(self):
            return defer.succeed(Fernet.generate_key())

        def callRemote(self, methodName, *args, **kwargs):
            if methodName == "getConfigProperties":
                return self.remote_propertyItems()
            elif methodName == "getThresholdClasses":
                return self.remote_getThresholdClasses()
            elif methodName == "getCollectorThresholds":
                return self.remote_getCollectorThresholds()
            elif methodName == "getDeviceConfigs":
                return self.remote_getDeviceConfigs(args)
            elif methodName == "getEncryptionKey":
                return self.remote_getEncryptionKey()

    def getRemoteConfigServiceProxy(self):
        return MyCollector.MyConfigServiceProxy()

    def configureRRD(self, rrdCreateCommand, thresholds):
        pass


class Dummy(object):
    pass


class MyPrefs(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        self.collectorName = "testcollector"
        self.options = Dummy()
        self.options.monitor = "localhost"


class TestConfig(BaseTestCase):
    def setUp(self):
        zope.component.provideUtility(MyCollector(), ICollector)

    def testPropertyItems(self):
        def validate(result):
            self.assertEquals(result["name"], "foobar")
            self.assertEquals(result["foobar"], "abcxyz")
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()
        d = cfgService.getPropertyItems(prefs)
        d.addBoth(validate)
        return d

    def testThresholdClasses(self):
        def validate(result):
            self.assertTrue("Products.ZenModel.FooBarThreshold" in result)
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getThresholdClasses(prefs)
        d.addBoth(validate)
        return d

    def testThresholds(self):
        def validate(result):
            self.assertTrue("yabba dabba do" in result)
            self.assertTrue("ho ho hum" in result)
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getThresholds(prefs)
        d.addBoth(validate)
        return d

    def testConfigProxies(self):
        def validate(result):
            self.assertTrue("hmm" in result)
            self.assertFalse("abcdef" in result)
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getConfigProxies(prefs)
        d.addBoth(validate)
        return d

    def testCrypt(self):
        cfgService = ConfigurationProxy()

        s = "this is a string I wish to encrypt"

        def validate_encrypt(result):
            self.assertTrue(result != s)
            return result

        def validate_decrypt(result):
            self.assertTrue(result == s)
            return result

        d = cfgService.encrypt(s)
        d.addBoth(validate_encrypt)
        d.addCallback(cfgService.decrypt)
        d.addBoth(validate_decrypt)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestConfig))
    return suite
