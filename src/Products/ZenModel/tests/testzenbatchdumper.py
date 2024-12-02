##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import logging

from DateTime import DateTime
from StringIO import StringIO
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.BatchDeviceLoader import BatchDeviceLoader
from Products.ZenModel.BatchDeviceDumper import BatchDeviceDumper

class FakeConfigs: pass

class FakeOptions:
    def __init__(self):
        self.nocommit = True
        self.noorganizers = False
        self.must_be_resolvable = False


class Testzenbatchdumper(BaseTestCase):

    def afterSetUp(self):
        super(Testzenbatchdumper, self).afterSetUp()

        self.zdumper = BatchDeviceDumper(noopts=1)
        self.zdumper.options = FakeOptions()
        self.zdumper.options.regex = '.*'
        self.zdumper.options.prune = False
        self.zdumper.options.root = '/zport/dmd/Devices/TestZenBatchDumper'

        self.zloader = BatchDeviceLoader(noopts=1)
        self.zloader.options = FakeOptions()
        self.zloader.options.nomodel = True
        self.zloader.options.nocommit = False

        # Ensure that both commands get
        # a real database connection
        self.zdumper.dmd = self.zloader.dmd

        self.log = logging.getLogger("zen.BatchDeviceDumper")
        self.zdumper.log = self.log
        self.zloader.log = logging.getLogger("zen.BatchDeviceLoader")

        # Actually add the organizer we use in testing
        testRoot = self.zdumper.options.root.rsplit('/', 1)[1]
        self.zdumper.dmd.Devices.manage_addOrganizer(testRoot)

    def testDump(self):
        olympics = DateTime("2010/02/28")
        configs = ["/Devices/TestZenBatchDumper", "device1 cDateTest=%s" % repr(olympics)]
        device_list, unparseable = self.zloader.parseDevices(configs)
        self.zloader.processDevices(device_list)

        outFile = StringIO()
        numDevs = self.zdumper.listDeviceTree(outFile)

        total = len([d for d in self.zdumper.root.getSubDevices() ])
        self.assert_(total > 0, "Didn't load any devices")
        self.assert_(numDevs['Devices'] == total,
            "Dumped %d of %d devices" % ( numDevs['Devices'], total))
        outText = outFile.getvalue()
        outFile.close()

        self.log.info(outText)
        outConfigs = outText.split('\n')
        out_device_list, unparseable = self.zloader.parseDevices(outConfigs)
        self.assert_(numDevs['Devices'] == len(out_device_list))
        dev = self.zloader.dmd.Devices.findDevice('device1')
        self.assert_(dev.cDateTest == olympics)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Testzenbatchdumper))
    return suite
