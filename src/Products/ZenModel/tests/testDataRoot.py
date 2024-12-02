##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
  
from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.Organizer import Organizer

class TestDataRoot(ZenModelBaseTest):

    def testFindChild(self):
        org = self.create(self.dmd, Organizer, 'org')
        org.dmdRootName = 'org'
        foo = org.createOrganizer('/foo')
        bar = org.createOrganizer('/foo/bar')
        quux1 = org.createOrganizer('/quux1')
        self.assertRaises(AttributeError, self.dmd.findChild, '')
        self.assertEqual(bar, self.dmd.findChild('org/foo/bar'))
        self.assertRaises(AttributeError, self.dmd.findChild, 'org/foo/quux1')
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDataRoot))
    return suite

if __name__=='__main__':
    framework()
