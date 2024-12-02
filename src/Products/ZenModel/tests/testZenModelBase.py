##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
  
from ZenModelBaseTest import ZenModelBaseTest

class TestZenModelBase(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestZenModelBase, self).afterSetUp()
        devices = self.dmd.Devices
        devices.createOrganizer("/Server")

    def testGetIconPath(self):
        self.dmd.Devices.Server.zIcon = '/zport/dmd/img/icons/server.png'
        d = self.dmd.Devices.Server.createInstance('test')
        self.assertEqual(d.getIconPath(), '/zport/dmd/img/icons/server.png')

    def testGetPrimaryDmdId(self):
        d = self.dmd.Devices.Server.createInstance('test')
        self.assertEqual(d.getPrimaryDmdId(), '/Devices/Server/devices/test')
        self.assertEqual(d.getPrimaryDmdId('Devices'), '/Server/devices/test')
        self.assertEqual(d.getPrimaryDmdId('Devices','devices'), '/Server/test')

    def testGetUnusedId(self):
        id1 = self.dmd.Devices.getUnusedId('devices', 'dev')
        self.assertEqual(id1, 'dev')
        self.dmd.Devices.createInstance(id1)
        id2 = self.dmd.Devices.getUnusedId('devices', 'dev')
        self.assertEqual(id2, 'dev2')
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenModelBase))
    return suite

if __name__=='__main__':
    framework()
