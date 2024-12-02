##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest

from mock import patch
from zope.interface.verify import verifyClass

from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.tests.base import EventTestCase
from Products.Zuul.interfaces import IProcessNode
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.interfaces import IProcessFacade
from Products.Zuul.infos.process import ProcessNode
from Products.Zuul.infos.process import ProcessInfo
from Products.Zuul.facades.processfacade import ProcessFacade
from Products.ZenModel.OSProcessOrganizer import manage_addOSProcessOrganizer

class ProcessFacadeTest(EventTestCase, ZuulFacadeTestCase):

    def afterSetUp(self):
        super(ProcessFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('process', self.dmd)
        manage_addOSProcessOrganizer(self.dmd.Processes, 'foo')
        self.dmd.Processes.foo.manage_addOSProcessClass('bar')

    def test_interfaces(self):
        verifyClass(IProcessNode, ProcessNode)
        verifyClass(IProcessInfo, ProcessInfo)
        verifyClass(IProcessFacade, ProcessFacade)

    def test_getTree(self):
        """
        NOTE: The process tree only returns organizers, not process classes
        """
        root = self.facade.getTree('/zport/dmd/Processes')
        self.assertEqual('.zport.dmd.Processes', root.id)
        self.assertEqual('Processes', root.text['text'])
        self.assertEqual(1, root.text['count'])
        self.assertEqual('instances', root.text['description'])
        self.failIf(root.leaf)
        children = list(root.children)
        self.assertEqual(1, len(children))
        foo = children[0]
        self.assertEqual('/zport/dmd/Processes/foo', foo.uid)
        self.assertEqual('.zport.dmd.Processes.foo', foo.id)
        self.assertEqual('Processes/foo', foo.path)
        self.assertEqual('foo', foo.text['text'])
        self.assertEqual(1, foo.text['count'])
        self.assertEqual('instances', foo.text['description'])
        self.failIf(foo.leaf)
        fooChildren = list(foo.children)
        self.assertEqual(0, len(fooChildren))

        obj = Zuul.marshal(root)
        self.assertEqual('.zport.dmd.Processes', obj['id'])
        self.assertEqual('Processes', obj['text']['text'])
        self.assertEqual(1, obj['text']['count'])
        self.assertEqual('instances', obj['text']['description'])
        self.assertEqual(False, obj['leaf'])
        self.assertEqual(1, len(obj['children']))
        fooObj = obj['children'][0]
        self.assertEqual('/zport/dmd/Processes/foo', fooObj['uid'])
        self.assertEqual('.zport.dmd.Processes.foo', fooObj['id'])
        self.assertEqual('Processes/foo', fooObj['path'])
        self.assertEqual('foo', fooObj['text']['text'])
        self.assertEqual(False, fooObj['leaf'])

    def test_getInfo(self):
        obj = self.facade.getInfo('/zport/dmd/Processes/foo/osProcessClasses/bar')
        self.assertEqual('bar', obj.name)
        data = Zuul.marshal(obj)
        self.assertEqual('bar', data['name'])
        data = {'name': 'barbar'}
        Zuul.unmarshal(data, obj)
        self.assertEqual('barbar', obj.name)

    @patch("Products.Zuul.facades.processfacade.getFacade")
    def test_getDevices(self, getFacade):
        device = self.dmd.Devices.createInstance('quux')
        uid = '/zport/dmd/Processes/foo/osProcessClasses/bar'
        device.os.addOSProcess(uid, 'bar', True)
        deviceInfos = list(self.facade.getDevices(uid))
        self.assertEqual(1, len(deviceInfos))
        deviceInfo = deviceInfos[0]

        self.assertEqual('quux', deviceInfo.getDevice())

    @patch("Products.ZenModel.EventView.EventView.getStatus")
    def test_getInstances(self, getStatus):
        device = self.dmd.Devices.createInstance('quux')
        uid = '/zport/dmd/Processes/foo/osProcessClasses/bar'
        device.os.addOSProcess(uid, 'bar', True)
        getStatus.return_value = 0

        instanceInfos = list(self.facade.getInstances(uid))
        self.assertEqual(1, len(instanceInfos))
        instanceInfo = instanceInfos[0]
        self.assertEqual('quux', instanceInfo.device.getDevice())
        self.assertEqual('bar', instanceInfo.name)
        self.assertEqual(True, instanceInfo.monitor)
        self.assertEqual('Up', instanceInfo.status)

    def test_deleteProcessClassRemovesInstances(self):
        device = self.dmd.Devices.createInstance('quux')
        uid = '/zport/dmd/Processes/foo/osProcessClasses/bar'
        self.assertEqual(0, len(device.os.processes()))
        device.os.addOSProcess(uid, 'bar', True)
        self.assertEqual(1, len(device.os.processes()))
        self.facade.deleteNode(uid)
        self.assertEqual(0, len(device.os.processes()))

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ProcessFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
