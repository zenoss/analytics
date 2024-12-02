##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from zope.interface.verify import verifyClass
from Products.ZenModel.IpService import IpService
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.ZenModel.Service import Service
from Products.Zuul.interfaces import IComponent

class ServiceFacadeTest(ZuulFacadeTestCase):

    def afterSetUp(self):
        super(ServiceFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('service', self.dmd)

    def test_interfaces(self):
        verifyClass(IComponent, Service)

    def test_getInstances(self):
        device = self.dmd.Devices.createInstance('foo')
        device.os.ipservices._setObject('tcp_00121', IpService('tcp_00121'))
        bar = device.os.ipservices()[0]
        bar.port = 121
        bar.protocol = 'tcp'
        bar.setServiceClass({'protocol':'tcp', 'port':121})
        self.assertEqual(1, len(self.dmd.Services.IpService.serviceclasses()))
        ipServiceClass = self.dmd.Services.IpService.serviceclasses()[0]
        self.assertEqual(1, len(ipServiceClass.instances()))
        uid = '/zport/dmd/Services/IpService/serviceclasses/tcp_00121'
        self.dmd.Devices.reIndex()
        instanceInfos = list(self.facade.getInstances(uid))
        self.assertEqual(1, len(instanceInfos))
        instanceInfo = instanceInfos[0]
        self.assertEqual('foo', instanceInfo.device.getDevice())
        self.assertEqual('tcp_00121', instanceInfo.name)
        self.assertEqual('None', instanceInfo.status)

    def test_deleteServiceClassRemovesInstances(self):
        device = self.dmd.Devices.createInstance('foo')
        uid = '/zport/dmd/Services/IpService/serviceclasses/tcp_00121'
        self.assertEqual(0, len(device.os.ipservices()))
        device.os.ipservices._setObject('tcp_00121', IpService('tcp_00121'))
        bar = device.os.ipservices()[0]
        bar.port = 121
        bar.protocol = 'tcp'
        bar.setServiceClass({'protocol':'tcp', 'port':121})
        self.assertEqual(1, len(device.os.ipservices()))
        self.facade.deleteNode(uid)
        self.assertEqual(0, len(device.os.ipservices()))


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ServiceFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
