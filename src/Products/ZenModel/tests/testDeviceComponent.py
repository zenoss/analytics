##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import time

from DateTime import DateTime

from Acquisition import aq_base
from Products.ZenModel.Exceptions import *

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.IpService import IpService
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenRelations.RelSchema import ToOne, ToManyCont


class SubComponent(IpService):
    _relations = (("superComponent", ToOne(ToManyCont, 'Products.ZenModel.IpService.IpService', 'subcomponents')),
                  ("subcomponents",  ToManyCont(ToOne, "Products.ZenModel.tests.testDeviceComponent.SubSubComponent", "superComponent")),
                  )

class SubSubComponent(SubComponent):
    _relations = ("superComponent", ToOne(
          ToManyCont,
          'Products.ZenModel.tests.testDeviceComponent.SubComponent',
          'subcomponents')),


IpService._relations = IpService._relations + (("subcomponents",  ToManyCont(ToOne, "Products.ZenModel.tests.testDeviceComponent.SubComponent", "superComponent")),)


class TestDeviceComponent(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestDeviceComponent, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = IpService('ipsvc')
        self.dev.os.ipservices._setObject('ipsvc',tmpo)
        tmpo.port = 121
        tmpo.protocol = 'tcp'
        self.ipsvc = self.dev.os.ipservices()[0]

        self.ipsvc.setServiceClass({'protocol':'tcp','port':121})
        self.sc = self.dmd.Services.IpService.serviceclasses.tcp_00121

    def test_setAqProperty(self):

        self.sc.zFailSeverity = 2

        self.ipsvc.setAqProperty('zFailSeverity', 2, 'int')
        self.assertEqual(self.ipsvc.hasProperty('zFailSeverity'), False)

        self.ipsvc.setAqProperty('zFailSeverity', 5, 'int')
        self.assertEqual(aq_base(self.ipsvc).zFailSeverity, 5)

        self.ipsvc.setAqProperty('zFailSeverity', 3, 'int')
        self.assertEqual(aq_base(self.ipsvc).zFailSeverity, 3)

        self.ipsvc.setAqProperty('zFailSeverity', 2, 'int')
        self.assertEqual(self.ipsvc.hasProperty('zFailSeverity'), False)


    def test_getSubComponentsNoIndexGen(self):
        # create a sub component
        comp = self.ipsvc
        sub = SubComponent('pepe')
        comp.subcomponents._setObject('pepe', sub)

        # call get sub component
        subcomps = comp.getSubComponentsNoIndexGen()

        # verify that we have that object
        hasPepe = False
        for subcomp in subcomps:
            if subcomp.id == 'pepe':
                hasPepe = True
        self.assertTrue(hasPepe, 'getSubComponentsNoIndexGen was unable to find a subcomponent')

    def test_subsubComponent(self):
        # create sub component
        comp = self.ipsvc
        sub = SubComponent('pepe')
        comp.subcomponents._setObject('pepe', sub)

        # create sub sub component
        subsub = SubSubComponent('pepe1')
        comp.subcomponents.pepe.subcomponents._setObject('pepe1', subsub)

        # create an object directly on subsub
        comp.subcomponents.pepe.subcomponents.pepe1._setObject('pepe2', SubSubComponent('pepe2'))

        objs = []
        for subcomp in comp.getSubComponentsNoIndexGen():
            objs.append(subcomp)
        self.assertEqual(len(objs), 3)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDeviceComponent))
    return suite

if __name__=="__main__":
    framework()
