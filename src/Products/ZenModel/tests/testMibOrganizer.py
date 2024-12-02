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
from Products.ZenModel.MibOrganizer import *
from Products.ZenModel.MibOrganizer import _oid2name
from Products.Zuul import getFacade
from ZenModelBaseTest import ZenModelBaseTest


class MockBrain(object):

    def __init__(self, oid=None, id=None):
        self.oid = oid
        self.id = id


class MockCatalog(object):

    def __init__(self, *brains):
        self.brains = brains
        
    def __call__(self, **query):
        matches = list(self.brains[:])
        for brain in self.brains:
            for query_key in query.keys():
                if not hasattr(brain, query_key):
                    raise Exception('brain is missing %s' % query_key)
                if getattr(brain, query_key) != query[query_key]:
                    matches.remove(brain)
                    break
        return matches


class TestOid2Name(ZenModelBaseTest):
    """tests the oid2name function
    """
    
    def runTest(self):
        brain = MockBrain(oid='1.3.6.1.4.1.4743.1.2.2.66',
                          id='expedIfBssAAAVlanAtts')
        self.mibSearch = MockCatalog(brain)
        
        # exact matching without stripping
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66', 'expedIfBssAAAVlanAtts',
            exactMatch=True, strip=False)
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66.0', '',
            exactMatch=True, strip=False)
        
        # exact matching with stripping
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66', 'expedIfBssAAAVlanAtts',
            exactMatch=True, strip=True,)
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66.0', '',
            exactMatch=True, strip=True)

        # partial matching without stripping
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66', 'expedIfBssAAAVlanAtts',
            exactMatch=False, strip=False)
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66.0', 'expedIfBssAAAVlanAtts.0',
            exactMatch=False, strip=False)

        # partial matching with stripping
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66', 'expedIfBssAAAVlanAtts',
            exactMatch=False, strip=True)
        self.doassert(
            '.1.3.6.1.4.1.4743.1.2.2.66.0', 'expedIfBssAAAVlanAtts',
            exactMatch=False, strip=True)
    
    
    def doassert(self, oid, expected, exactMatch, strip):
        actual = _oid2name(self.mibSearch, oid, exactMatch, strip)
        self.assertEqual(expected, actual, 
                         'expected "%s" but got "%s"' % (expected, actual))


class TestMibOrganizer(ZenModelBaseTest):


    def testMibOrganizer(self):
        mibOrg = self.dmd.Mibs
        mod = mibOrg.createMibModule('mod')
        two = mibOrg.createMibModule('two','/layer')
        self.assert_(mod in mibOrg.mibs())
        self.assert_(mibOrg.countClasses() == 2)
        self.assert_('layer' in mibOrg.childIds())
        layer = mibOrg.getOrganizer('layer')
        self.assert_(two in layer.mibs())
        layer.moveMibModules('/',['two'])
        self.assert_(two not in layer.mibs())
        self.assert_(two in mibOrg.mibs())
        mibOrg.removeMibModules(['two'])
        self.assert_(two not in mibOrg.mibs())
        three = mibOrg.manage_addMibModule('three')
        self.assert_(three in mibOrg.mibs())
        

    def testMibModule(self):
        mibOrg = self.dmd.Mibs
        mod = mibOrg.createMibModule('mod')

        self.assert_(mod.getModuleName() == 'mod')

        mod.createMibNode(id = 'node', moduleName = 'mod', nodetype = 'MibNode'\
                          , oid = '1', status = 'ok', description = 'my mib'\
                         )
                         
        self.assert_(mod.nodeCount() == 1)
        self.assert_(mibOrg.name2oid('node') == '1')
        self.assert_(mibOrg.oid2name('1') == 'node')
        
        mod.createMibNotification(id = 'notification', moduleName = 'mod',\
                                  nodetype = 'MibNotification', oid = '2',\
                                  status = 'ok', description = 'my note'\
                                 )
        
        self.assert_(mod.notificationCount() == 1)
        self.assert_(mibOrg.name2oid('notification') == '2')
        self.assert_(mibOrg.oid2name('2') == 'notification')


    def testOrganizer(self):
        mibOrg = self.dmd.Mibs
        subOrg = mibOrg.createOrganizer('/sub')
        mod = mibOrg.createMibModule('mod', '/modLoc')
        modLoc = mibOrg.getOrganizer('modLoc')
        moveMe = mibOrg.createOrganizer('/mobile')
        # there's more in mibOrg than is defined here, due to the test case
        # setup
        self.assert_(mibOrg.countChildren() == 3)
        self.assert_(subOrg in mibOrg.getSubOrganizers())
        self.assert_(modLoc in mibOrg.getSubOrganizers())
        self.assert_('/sub' in mibOrg.getOrganizerNames())
        self.assert_('/modLoc' in mibOrg.getOrganizerNames())
        facade = getFacade('device', self.dmd)
        mibOrg.moveOrganizer('/sub', ['mobile'])
        self.assert_(moveMe not in mibOrg.children())
        self.assert_(moveMe in subOrg.children())
        facade.deleteNode("/zport/dmd/Mibs/sub")
        facade.deleteNode("/zport/dmd/Mibs/modLoc")
        
        self.assert_(subOrg not in mibOrg.getSubOrganizers())
        self.assert_(modLoc not in mibOrg.getSubOrganizers())
        self.assert_(moveMe not in mibOrg.getSubOrganizers())
        self.assert_(mibOrg.countClasses() == 0)
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestOid2Name))
    suite.addTest(makeSuite(TestMibOrganizer))
    return suite

if __name__=="__main__":
    framework()
