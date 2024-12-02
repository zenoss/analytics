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

from Products.ZenModel.ZenossSecurity import *

from Products.Zuul.catalog.interfaces import IModelCatalogTool

from ZenModelBaseTest import ZenModelBaseTest

idsort = lambda a,b: cmp(a.id, b.id)

class TestDeviceOrganizers(ZenModelBaseTest):

    def assertSameObs(self, *args):
        map(lambda x:x.sort(idsort), args)
        return self.assertEqual(*args)

    def afterSetUp(self):
        super(TestDeviceOrganizers, self).afterSetUp()
        self.catalog = IModelCatalogTool(self.dmd.Devices)

        orgs = ("/aa/bb", "/aa/cc", "/bb/aa", "/bb/cc")

        devices = self.dmd.Devices

        for org in orgs:
            devices.createOrganizer(org)

        self.ab = devices.aa.bb.createInstance('ab')
        self.ac = devices.aa.cc.createInstance('ac')
        self.ba = devices.bb.aa.createInstance('ba')
        self.bc = devices.bb.cc.createInstance('bc')

    def testDeviceClassSubDevices(self):
        """
        Test that all the varieties of getSubDevices return the same (correct)
        thing.
        """
        control = [self.ab, self.ac, self.ba, self.bc]

        test = self.dmd.Devices.getSubDevices()
        testgen = list(self.dmd.Devices.getSubDevicesGen())
        testrec = self.dmd.Devices.getSubDevices_recursive()
        testgenrec = list(self.dmd.Devices.getSubDevicesGen_recursive())

        for resultset in (test, testgen, testrec, testgenrec):
            self.assertSameObs(control, resultset)

    def testIndexingWhenMoveDevices(self):
        """
        Test that the index updates when moving devices from one DeviceClass to
        another.
        """
        self.dmd.Devices.moveDevices('/aa/bb', ['ba', 'ac'])
        control = [self.ac, self.ba, self.ab]
        test = self.dmd.Devices.aa.bb.getSubDevices()
        self.assertSameObs(control, test)

    def testOrganizerRecursion(self):
        """
        Test that parents return all their children.
        """
        adevs = [self.ac, self.ab]
        self.assertSameObs(self.dmd.Devices.aa.getSubDevices(), adevs)

    def testSamePathDifferentRoot(self):
        """
        Make sure that catalog works with similar but unrelated paths.
        """
        self.ac.setLocation("/aa/bb")
        self.ab.setGroups("/aa/bb")
        self.assert_(len(self.dmd.Groups.aa.bb.getSubDevices())==1)
        self.assert_(len(self.dmd.Locations.aa.bb.getSubDevices())==1)

    def testOrganizerSubDevices(self):
        """
        Test that getSubDevices works properly for non-DeviceClass organizers.
        """
        self.ac.setLocation("/aa/bb")
        self.assertSameObs(self.dmd.Locations.aa.getSubDevices(), [self.ac])
        self.ab.setLocation("/aa/bb")
        self.assertSameObs(self.dmd.Locations.aa.getSubDevices(), [self.ac, self.ab])

        self.ba.setGroups(("/aa/cc",))
        self.ab.setGroups(("/aa/bb",))
        self.bc.setGroups(["/aa/bb", "/aa/cc"])
        self.assertSameObs(self.dmd.Groups.aa.bb.getSubDevices(),[self.bc, self.ab])
        self.assertSameObs(self.dmd.Groups.aa.cc.getSubDevices(),[self.bc, self.ba])

        self.ba.setSystems(("/aa/cc",))
        self.ab.setSystems(("/aa/bb",))
        self.bc.setSystems(["/aa/bb", "/aa/cc"])
        self.assertSameObs(self.dmd.Systems.aa.bb.getSubDevices(),[self.bc, self.ab])
        self.assertSameObs(self.dmd.Systems.aa.cc.getSubDevices(),[self.bc, self.ba])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDeviceOrganizers))
    return suite

if __name__=="__main__":
    framework()
