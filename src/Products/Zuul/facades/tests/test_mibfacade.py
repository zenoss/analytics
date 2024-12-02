##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
#import zope.component
from zope.interface.verify import verifyClass
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.interfaces import IMibOrganizerInfo
from Products.Zuul.infos.mib import MibOrganizerInfo

class MibFacadeTest(ZuulFacadeTestCase):
    """
    Because MIBs are so prone to getting messed up, we need
    to test the trees that get generated from these sources.
    """

    def afterSetUp(self):
        super(MibFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('mibs', self.dmd)
        self.mibName = 'myTestMIB'
        self.mib = self.dmd.Mibs.createMibModule(self.mibName)

    def _addNode(self, name, oid, **kwargs):
        self.mib.createMibNode(id=name, moduleName=self.mibName,
                nodetype='MibNode', oid=oid, **kwargs)

    def _addTrap(self, name, oid, **kwargs):
        self.mib.createMibNotification(id=name, moduleName=self.mibName,
                nodetype='MibNotification', oid=oid, **kwargs)

    def test_interfaces(self):
        verifyClass(IMibOrganizerInfo, MibOrganizerInfo)

    def Xtest_emptyMib(self):
        nodeTree = self.facade.getMibNodeTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(nodeTree is None)
        trapTree = self.facade.getMibTrapTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(trapTree is None)

    def test_mib_organizers(self):
        orgTree = self.facade.getOrganizerTree('/zport/dmd/Mibs')
        self.assert_(len([mib for mib in orgTree.children]) == 1)

        self.dmd.Mibs.createMibModule('mib2', '/folder1')
        self.assert_(len([mib for mib in orgTree.children]) == 2)

    def Xtest_no_nodes(self):
        self._addTrap('topLevelOid',  '1.3.6.4.1.7')
        self._addTrap('nextLevelOid', '1.3.6.4.1.7.2')

        nodeTree = self.facade.getMibNodeTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(nodeTree is None)

        trapTree = self.facade.getMibTrapTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(trapTree is not None)
        self.assert_(trapTree.id == '.zport.dmd.Mibs.mibs.myTestMIB.notifications.topLevelOid')
        self.assert_(len(trapTree.children) == 1)
        self.assert_(trapTree.children[0].id == '.zport.dmd.Mibs.mibs.myTestMIB.notifications.nextLevelOid')

    def Xtest_no_traps(self):
        # Since the facade uses the same code underneath for traps and nodes,
        # this test basically ensures that self._addNode() works correctly
        self._addNode('topLevelOid',  '1.3.6.4.1.7')
        self._addNode('nextLevelOid', '1.3.6.4.1.7.2')

        nodeTree = self.facade.getMibNodeTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(nodeTree is not None)
        self.assert_(nodeTree.id == '.zport.dmd.Mibs.mibs.myTestMIB.nodes.topLevelOid')
        self.assert_(len(nodeTree.children) == 1)
        self.assert_(nodeTree.children[0].id == '.zport.dmd.Mibs.mibs.myTestMIB.nodes.nextLevelOid')

        trapTree = self.facade.getMibTrapTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(trapTree is None)

    def test_missing_base_oids(self):
        # All of these OIDs are siblings -- need to create a fake parent node
        self._addNode('topLevelOid3',  '1.3.6.4.1.3')
        self._addNode('topLevelOid2',  '1.3.6.4.1.2')
        self._addNode('topLevelOid1',  '1.3.6.4.1.1')
        self._addNode('topLevelOid4',  '1.3.6.4.1.4')

        nodeTree = self.facade.getMibNodeTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(nodeTree is not None)
        self.assert_(len(nodeTree.children) == 4, "Fake parent OID missing children!")

    def Xtest_missing_children_oids(self):
        self._addNode('topLevelOid',  '1.3.6.4.1')
        # It's always the odd ones, right?
        self._addNode('topLevelOid1',  '1.3.6.4.1.1')
        self._addNode('topLevelOid3',  '1.3.6.4.1.3')
        self._addNode('topLevelOid5',  '1.3.6.4.1.5')
        self._addNode('topLevelOid7',  '1.3.6.4.1.7')

        nodeTree = self.facade.getMibNodeTree('/zport/dmd/Mibs/mibs/myTestMIB')
        self.assert_(nodeTree is not None)
        self.assert_(len(nodeTree.children) == 4)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(MibFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
