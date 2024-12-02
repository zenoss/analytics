##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenEvents.events2.processing import Manager
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class DeviceIdTest(BaseTestCase):

    def test0(self):
        #Set up a device with a single interface with two IP addresses
        device = self.dmd.Devices.createInstance('mydevice')
        device.setManageIp('10.10.10.1')
        device.os.addIpInterface('eth0', False)
        iface = device.os.interfaces()[0]
        iface.addIpAddress('10.10.10.2')
        iface.addIpAddress('10.10.10.3')

        device_uuid = IGlobalIdentifier(device).getGUID()
        manager = Manager(self.dmd)
        def test(id, ip, msg, expected = device_uuid):
            self.assertEquals(manager.findDeviceUuid(id, ip), expected, msg)

        test('mydevice', '', "failed to find by device name")
        test('10.10.10.1', '', "failed to find by device name == IP")
        test('dev', '10.10.10.1', "failed to find by device's manageIP")
        test('dev', '10.10.10.2', "failed to find by interface's primary IP")
        test('dev', '10.10.10.3', "failed to find by interface's secondary IP")
        test('dev', '10.10.10.4', "failed missing IP test", None)

def test_suite():
    from unittest import TestSuite, makeSuite
    tests = []
    tests.append(makeSuite(DeviceIdTest))
    suite = TestSuite()
    suite.addTests(tests)
    return suite
