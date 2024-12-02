##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.ComponentGroup import ComponentGroup

class ComponentGroupTest(BaseTestCase):

    def afterSetUp(self):
        super(ComponentGroupTest, self).afterSetUp()
        foo = ComponentGroup('ComponentGroups')
        self.dmd._setObject('ComponentGroups', foo)
        # add a component
        device = self.dmd.Devices.createInstance('test')
        device.os.addIpInterface('eth0', True)
        interface = device.os.interfaces()[0]
        groupNames = set(interface.getComponentGroupNames())
        groupNames.add(self.dmd.ComponentGroups.getOrganizerName())
        interface.setComponentGroups(list(groupNames))

    def testCanCreateComponentGroups(self):
        self.assertTrue(self.dmd.ComponentGroups)

    def testCanCreateSubOrganizers(self):
        self.dmd.ComponentGroups.createOrganizer("/test/test1/test2/test3")
        self.assertTrue(self.dmd.ComponentGroups.test.test1.test2.test3)

    def testCanRemoveSubOrganizers(self):
        self.dmd.ComponentGroups.createOrganizer("/test/test1/test2/test3")
        self.dmd.ComponentGroups._delObject('test')
        self.assertFalse(self.dmd.ComponentGroups._getOb('test', None))

    def testCanGetPrettyLink(self):
        link = self.dmd.ComponentGroups.getPrettyLink()
        self.assertTrue('/ComponentGroups' in link)

    def testAdministrativeRoles(self):
        user = self.dmd.ZenUsers.getUserSettings('pepe')
        org = self.dmd.ComponentGroups.createOrganizer('test')
        org.manage_addAdministrativeRole(user.id)
        self.assertEquals(len(org.adminRoles()), 1)

        # edit
        org.manage_editAdministrativeRoles([user.id], ['ZenManager'])
        self.assertEquals(org.adminRoles()[0].role, 'ZenManager')

        # delete
        org.manage_deleteAdministrativeRole([user.id])
        self.assertEquals(org.adminRoles(), [])

    def testCanGetComponents(self):
        comps = self.dmd.ComponentGroups.getComponents()
        self.assertEquals(len(comps), 1)
        interface = self.dmd.Devices.devices.test.os.interfaces()[0]
        self.assertEquals(interface.getComponentGroupNames(), ["/"])

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ComponentGroupTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
