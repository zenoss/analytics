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
  
from Products.ZenModel.Exceptions import *
from Products.ZenModel.Organizer import *
from Products.Zuul import getFacade
from ZenModelBaseTest import ZenModelBaseTest
  
class TestOrganizer(ZenModelBaseTest):
  
    def testOrganizer(self):
        org = self.create(self.dmd, Organizer, "org")
        org.dmdRootName = "org"
        bar = org.createOrganizer("/foo/bar")
        foo = org._getOb("foo")
        
        self.assert_(foo in org.children())
        self.assert_("foo" in org.childIds())

        self.assert_(org.countChildren() == 2)
        self.assert_(org.unrestrictedTraverse("foo/bar") == bar)
        self.assert_(org.getOrganizer("/foo/bar") == bar)
        self.assert_(bar.getOrganizerName() == "/foo/bar")

        self.assert_('/foo' in org.getOrganizerNames())
        self.assert_('/foo/bar' in org.getOrganizerNames())
        self.assert_('/foo' in org.deviceMoveTargets())
        self.assert_('/foo/bar' in org.deviceMoveTargets())
        self.assert_('/foo' in org.childMoveTargets())
        self.assert_('/foo/bar' in org.childMoveTargets())

        self.assert_(org.getDmdKey() == '/')
        self.assert_(foo in org.getSubOrganizers())
        self.assert_(bar in org.getSubOrganizers())

        self.assert_(org.getChildMoveTarget('/foo') == foo)
        self.assert_(org.getChildMoveTarget('/foo/bar') == bar)


    def testManageOrganizer(self):
        org = self.create(self.dmd,Organizer,'org')
        org.dmdRootName = "org"
        org.manage_addOrganizer('/foo/bar')
        org.manage_addOrganizer('/test/loc')
        org.manage_addOrganizer('/number/three')
        foo = org.getOrganizer('/foo')
        test = org.getOrganizer('/test')
        number = org.getOrganizer('/number')
        self.assert_(foo in org.children())
        self.assert_(test in org.children())
        self.assert_(number in org.children())
        facade = getFacade('device', self.dmd)
        facade.deleteNode('/'.join(foo.getPhysicalPath()))
        self.assert_(foo not in org.children())
        getFacade('device', self.dmd).deleteNode('/'.join(test.getPhysicalPath()))
        getFacade('device', self.dmd).deleteNode('/'.join(number.getPhysicalPath()))
        self.assert_(org.children() == [])
        
    def testGetOrganizer(self):
        """
        Tests to make sure that getOrganizer uses acquisition. Sets up org/foo
        and org/quux organizers and asks for org/foo/quux.
        """
        org = self.create(self.dmd, Organizer, "org")
        org.dmdRootName = "org"
        foo = org.createOrganizer("/foo")
        quux = org.createOrganizer("/quux2")
        self.assertEqual(quux, org.getOrganizer("/foo/quux2"))
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestOrganizer))
    return suite

if __name__=="__main__":
    framework()
