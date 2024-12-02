##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os, sys

if __name__ == "__main__":
    execfile(os.path.join(sys.path[0], "framework.py"))

from Products.ZenRelations.tests.TestSchema import *
from Products.ZenRelations.Exceptions import *

from ZenRelationsBaseTest import ZenRelationsBaseTest


class PrimaryPathManagerTest(ZenRelationsBaseTest):
    def testGetPrimaryPath(self):
        "relative primary path of a contained object"
        dev = self.build(self.app, Device, "dev")
        eth0 = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth0.getPrimaryPath() == ("dev", "interfaces", "eth0"))
        self.failUnless(eth0.getPrimaryId() == "dev/interfaces/eth0")

    def testGetPrimaryPath2(self):
        "absolute primary path of a contained object using fromNode"
        dev = self.build(self.dmd, Device, "dev")
        eth0 = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth0.getPrimaryPath("dev") == ("interfaces", "eth0"))
        self.failUnless(eth0.getPrimaryId("dev") == "/interfaces/eth0")

    def testGetPrimaryPath3(self):
        "absolute primary path of a related object using zPrimaryBasePath"
        dev = self.build(self.dmd, Device, "dev")
        group = self.create(self.dmd, Group, "group")
        dev.groups.addRelation(group)
        self.failUnless(
            dev.groups()[0].getPrimaryPath() == ("", "zport", "dmd", "group")
        )
        self.failUnless(dev.groups()[0].getPrimaryId() == "/zport/dmd/group")

    def testPrimaryAq(self):
        "primary acquisition chain of a related object"
        dev = self.build(self.dmd, Device, "dev")
        group = self.create(self.dmd, Group, "group")
        dev.groups.addRelation(group)
        chain = dev.groups()[0].aq_chain
        ids = [x.getId() for x in chain if hasattr(x, "getId")]
        self.failUnless(ids == ["group", "groups", "dev", "dmd", "zport", ""])
        chain = group.primaryAq().aq_chain
        ids = [x.getId() for x in chain if hasattr(x, "getId")]
        self.failUnless(ids == ["group", "dmd", "zport", ""])


class RelationshipManagerTest(ZenRelationsBaseTest):
    def testBuildRelations(self):
        "Check that relationships are built correctly."
        dev = self.build(self.dmd, Device, "dev")
        self.failUnless(
            getattr(dev, "location").meta_type == "ToOneRelationship"
        )
        self.failUnless(
            getattr(dev, "groups").meta_type == "ToManyRelationship"
        )
        self.failUnless(
            getattr(dev, "interfaces").meta_type == "ToManyContRelationship"
        )

    def testBuildRelationsWithInheritance(self):
        "Check that relationships are built correctly with inheritance."
        server = self.build(self.dmd, Server, "server")
        self.failUnless(
            getattr(server, "location").meta_type == "ToOneRelationship"
        )
        self.failUnless(
            getattr(server, "groups").meta_type == "ToManyRelationship"
        )
        self.failUnless(
            getattr(server, "interfaces").meta_type == "ToManyContRelationship"
        )
        self.failUnless(
            getattr(server, "admin").meta_type == "ToOneRelationship"
        )

    def testLookupRelationSchema(self):
        dev = self.build(self.dmd, Device, "dev")
        self.failUnless(dev.lookupSchema("location").remoteName == "devices")

    def testLookupRelationSchemaWithInheritance(self):
        dev = self.build(self.dmd, Server, "dev")
        self.failUnless(dev.lookupSchema("location").remoteName == "devices")
        self.failUnless(dev.lookupSchema("admin").remoteName == "server")

    def testSetObjectRM(self):
        """Make sure that _setObject returns id and sets object correctlly"""
        dev = self.build(self.dmd, Server, "dev")
        from OFS.Folder import Folder

        folder = Folder("folder")
        id = dev._setObject("folder", folder)
        self.assert_(id == "folder")
        self.assert_(dev._getOb(id) == folder)

    def testGetProperties(self):
        pass

    def testMoveMeBetweenRels(self):
        dev = self.create(self.dmd, Device, "dev")
        eth0 = self.create(dev.interfaces, IpInterface, "eth0")
        dev2 = self.create(self.dmd, Device, "dev2")
        eth0.moveMeBetweenRels(dev.interfaces, dev2.interfaces)
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(len(dev2.interfaces()) == 1)
        self.failUnless(dev2.interfaces.eth0.device() == dev2)

    def testMoveMeBetweenRels2(self):
        org1 = self.create(self.dmd, Organizer, "org1")
        org2 = self.create(self.dmd, Organizer, "org2")
        dev = self.create(self.dmd.org1.devices, Device, "dev")
        eth0 = self.create(dev.interfaces, IpInterface, "eth0")
        loc = self.create(self.dmd, Location, "anna")
        loc.devices.addRelation(dev)
        dev.moveMeBetweenRels(org1.devices, org2.devices)
        self.failUnless(len(org1.devices()) == 0)
        self.failUnless(len(org2.devices()) == 1)
        self.failUnless(org2.devices.dev.organizer() == org2)
        self.assert_(dev.interfaces.eth0)
        self.assert_(len(loc.devices()) > 0)


from Products.ZenRelations.ToOneRelationship import manage_addToOneRelationship


class ToOneRelationshipTest(ZenRelationsBaseTest):
    def testmanage_addToOneRelationship(self):
        """Test adding a to one relationship"""
        dev = Server("server", buildRelations=False)
        manage_addToOneRelationship(dev, "admin")
        self.failUnless(hasattr(dev, "admin"))

    def testmanage_addToOneRelationshipSchemaBad(self):
        """add a relationship with invalid schema"""
        dev = Server("server", buildRelations=False)
        self.failUnlessRaises(
            ZenSchemaError, manage_addToOneRelationship, dev, "lkjlkjlkjlkj"
        )

    def testaddRelationOneToOne(self):
        """Test addRelation in a one to one"""
        dev = self.create(self.app, Server, "dev")
        jim = self.create(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)

    def testaddRelationOneToOne2(self):
        """Test addRelation in where both sides of realtionship exist"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)

    def testaddRelationOneToOne3(self):
        """Test addRelation on the ToOneRelationship itself"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.admin.addRelation(jim)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)

    def testaddRelationOneToOneNone(self):
        """Test addRelation in a one to one with None"""
        dev = self.build(self.app, Server, "dev")
        self.failUnlessRaises(
            ZenRelationsError, dev.addRelation, "admin", None
        )

    def testaddRelationOneToOneOverwrite(self):
        """Test addRelation over write of relationship"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        nate = self.build(self.app, Admin, "nate")
        dev.addRelation("admin", jim)
        dev.addRelation("admin", nate)
        self.failUnless(dev.admin() == nate)
        self.failUnless(nate.server() == dev)
        self.failUnless(jim.server() == None)

    def testDeletingRelationship(self):
        """Test deleting the relationship object itself,
        make sure the link is removed"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        dev._delObject("admin")
        self.failIf(hasattr(dev, "admin"))
        self.failUnless(jim.server() == None)


# =============================================================================
# =============================================================================


class ToManyContRelationshipTest(ZenRelationsBaseTest):
    def testFindObjectsByIdOnCont(self):
        """Test removeRelation on a to many object itself"""
        dev = self.build(self.app, Device, "dev")
        self.create(dev.interfaces, IpInterface, "eth0")
        self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.findObjectsById("eth0")) == 1)

    def testaddRelationOneToManyCont(self):
        """Test froming a one to many contained relationship"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth in dev.interfaces())
        self.failUnless(eth.device() == dev)

    def testaddRelationOneToManyContSame(self):
        """Test setting the many side of one ToManycont twice with same object."""
        dev = self.create(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        dev.interfaces.addRelation(eth)
        self.failUnless(eth in dev.interfaces())
        self.failUnless(len(dev.interfaces()) == 1)
        self.failUnless(eth.device() == dev)

    def testDeleteFromOneToManyCont(self):
        """Delete RM from within a ToManyCon relationship"""
        dev = self.build(self.app, Device, "dev")
        eth0 = self.build(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth0 in dev.interfaces())
        dev.interfaces._delObject("eth0")
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(eth0.device() == None)

    def testremoveRelationOneToManyCont(self):
        """Test removing a one to many contained relationship"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth.device() == dev)
        dev.removeRelation("interfaces", eth)
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(eth.device() == None)

    def testremoveRelationOneToManyCont2(self):
        """Test removing a one to many contained relationship from relation"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth.device() == dev)
        dev.interfaces.removeRelation(eth)
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(eth.device() == None)

    def testremoveRelationOneToManyCont3(self):
        """Test removing all objects from one to many contained relationship"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces()) == 2)
        dev.removeRelation("interfaces")
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(eth.device() == None)
        self.failUnless(eth1.device() == None)

    def testremoveRelationOneToManyCont4(self):
        """remove all objs from one to many contained relationship from relation"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces()) == 2)
        dev.interfaces.removeRelation()
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(eth.device() == None)
        self.failUnless(eth1.device() == None)

    def testsetObjectOneToManyContH(self):
        """Test setObject on ToManyCont where there is a recursive relation"""
        org = self.build(self.app, Organizer, "root")
        child = Organizer("child")
        org.children._setObject("child", child)
        child = org.children._getOb("child")
        self.failUnless(child.parent() == org)
        self.failUnless(child in org.children())
        self.failUnless(org.parent() == None)

    def testObjectIdsOneToManyCont(self):
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.objectIds()) == 2)
        self.failUnless("eth0" in dev.interfaces.objectIds())
        self.failUnless("eth1" in dev.interfaces.objectIds())

    def testObjectIdsAllOneToManyCont(self):
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.objectIdsAll()) == 2)
        self.failUnless("eth0" in dev.interfaces.objectIdsAll())
        self.failUnless("eth1" in dev.interfaces.objectIdsAll())

    def testObjectValuesOneToManyCont(self):
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.objectValues()) == 2)
        self.failUnless(eth in dev.interfaces.objectValues())
        self.failUnless(eth1 in dev.interfaces.objectValues())

    def testObjectValuesAllOneToManyCont(self):
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.objectValuesAll()) == 2)
        self.failUnless(eth in dev.interfaces.objectValuesAll())
        self.failUnless(eth1 in dev.interfaces.objectValuesAll())

    def testObjectItemsOneToManyCont(self):
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.objectItems()) == 2)
        self.failUnless(("eth0", eth) in dev.interfaces.objectItemsAll())
        self.failUnless(("eth1", eth1) in dev.interfaces.objectItemsAll())

    def testObjectItemsAllOneToManyCont(self):
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.objectItemsAll()) == 2)
        self.failUnless(("eth0", eth) in dev.interfaces.objectItemsAll())
        self.failUnless(("eth1", eth1) in dev.interfaces.objectItemsAll())

    def testBeforeDeleteOneToManyCont(self):
        # First build the objects
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces()) == 2)

        # Hook in a handler
        seen = []

        def remove_handler(obj, event):
            seen.append(obj)

        from zope.component import provideHandler
        from OFS.interfaces import IObjectWillBeMovedEvent

        provideHandler(remove_handler, (IpInterface, IObjectWillBeMovedEvent))

        # Delete the relation and make sure the event is fired and the handler
        # picks it up
        dev.interfaces.removeRelation()
        self.failUnless(len(dev.interfaces()) == 0)
        self.failUnless(eth in seen)
        self.failUnless(eth1 in seen)

    def testAfterAddOneToManyCont(self):
        # Hook up a simple handler
        from zope.component import provideHandler
        from zope.container.interfaces import IObjectAddedEvent

        seen = []

        def add_handler(obj, event):
            seen.append(obj)

        provideHandler(add_handler, (IpInterface, IObjectAddedEvent))

        # Add the objects
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")

        # Make sure the events fired
        self.failUnless(eth in seen)
        self.failUnless(eth1 in seen)
        self.failUnless(len(dev.interfaces()) == 2)


class ToManyRelationshipTest(ZenRelationsBaseTest):
    def testFindObjectsByIdOnToMany(self):
        """Test removeRelation on a to many object itself"""
        dev = self.build(self.app, Device, "dev")
        group = self.build(self.app, Group, "group")
        group2 = self.build(self.app, Group, "group2")
        dev.groups.addRelation(group)
        dev.groups.addRelation(group2)
        self.failUnless(len(dev.groups.findObjectsById("group")) == 2)

    def testaddRelationOneToMany(self):
        """Test froming a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        loc = self.create(self.app, Location, "loc")
        loc.addRelation("devices", dev)
        self.failUnless(dev in loc.devices())
        self.failUnless(dev.location() == loc)

    def testaddRelationOneToMany2(self):
        """Test froming a one to many relationship reverse"""
        dev = self.create(self.app, Device, "dev")
        loc = self.create(self.app, Location, "loc")
        dev.addRelation("location", loc)
        self.failUnless(dev in loc.devices())
        self.failUnless(dev.location() == loc)

    def testaddRelationOneToManyOverwrite(self):
        """Test setting the one side of one to many twice with same object"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        riva = self.create(self.app, Location, "riva")
        dev.addRelation("location", anna)
        dev.addRelation("location", riva)
        self.failUnless(dev in riva.devices())
        self.failUnless(len(anna.devices()) == 0)
        self.failUnless(dev.location() == riva)

    def testaddRelationOneToManySame(self):
        """Test setting the many side of one to many twice with same object"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        anna.devices.addRelation(dev)
        self.failUnless(dev in anna.devices())
        self.failUnless(len(anna.devices()) == 1)
        self.failUnless(dev.location() == anna)
        anna.devices.addRelation(dev)
        self.failUnless(dev in anna.devices())
        self.failUnless(len(anna.devices()) == 1)
        self.failUnless(dev.location() == anna)

    def testaddRelationOnToMany(self):
        """Test addRelation on a to many object itself"""
        dev = self.create(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        anna.devices.addRelation(dev)
        self.failUnless(dev in anna.devices())
        self.failUnless(dev.location() == anna)

    def testaddRelationOnToManyMissing(self):
        """Test addRelation with missing rel on remote end"""
        dev = self.create(self.app, Device, "dev")
        dev._delObject("location")
        anna = self.build(self.app, Location, "anna")
        self.assertRaises(AttributeError, anna.devices.addRelation, dev)

    def test_delObjectOneToMany(self):
        """Test removing from a to many relationship"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        self.failUnless(dev.location() == anna)
        anna.devices._delObject(dev.getPrimaryId())
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())

    def testremoveRelationOneToMany(self):
        """Test removeRelation on a to many object itself"""
        dev = self.create(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        anna.devices.addRelation(dev)
        self.failUnless(dev.location() == anna)
        anna.devices.removeRelation()
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())
        self.failUnless(len(anna.devices()) == 0)

    def testremoveRelationOneToMany1(self):
        """Test removeRelation on a to many object itself"""
        dev = self.create(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        anna.devices.addRelation(dev)
        self.failUnless(dev.location() == anna)
        dev.location.removeRelation()
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())
        self.failUnless(len(anna.devices()) == 0)

    def testremoveRelationOneToMany2(self):
        """Test removing from a to many relationship with two objects"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        anna.addRelation("devices", dev2)
        self.failUnless(dev.location() == anna)
        self.failUnless(dev2.location() == anna)
        anna.removeRelation("devices", dev)
        self.failUnless(dev.location() == None)
        self.failIf(dev in anna.devices())
        self.failUnless(dev2 in anna.devices())

    def testremoveRelationOneToMany3(self):
        """Test removing from to one side of a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        self.failUnless(dev.location() == anna)
        dev.location.removeRelation(anna)
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())

    def testremoveRelationOneToMany4(self):
        """Test removing all from to one side of a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        anna.addRelation("devices", dev2)
        self.failUnless(len(anna.devices()) == 2)
        anna.removeRelation("devices")
        self.failUnless(len(anna.devices()) == 0)
        self.failUnless(dev.location() == None)
        self.failUnless(dev2.location() == None)

    def testremoveRelationOneToMany5(self):
        """Test removing non existant object from one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        anna = self.create(self.app, Location, "anna")
        dev.location.addRelation(anna)
        self.assertRaises(ObjectNotFound, anna.removeRelation, "devices", dev2)
        self.failUnless(dev2.location() == None)
        self.failUnless(dev.location() == anna)
        self.failUnless(dev in anna.devices())
        self.failUnless(len(anna.devices()) == 1)

    def testremoveRelationOneToMany6(self):
        """Test removing non existant object from one side of one to many rel"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        riva = self.create(self.app, Location, "riva")
        dev.location.addRelation(anna)
        self.assertRaises(ObjectNotFound, dev.removeRelation, "location", riva)
        self.failUnless(riva.devices() == [])
        self.failUnless(dev.location() == anna)
        self.failUnless(dev in anna.devices())
        self.failUnless(len(anna.devices()) == 1)

    def testObjectIdsOneToMany(self):
        """Test objectIds on a ToMany"""
        loc = self.create(self.app, Location, "loc")
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        loc.addRelation("devices", dev)
        loc.addRelation("devices", dev2)
        self.failUnless(len(loc.devices.objectIdsAll()) == 2)
        self.failUnless("dev" in loc.devices.objectIdsAll())
        self.failUnless("dev2" in loc.devices.objectIdsAll())
        self.failUnless(len(loc.devices.objectIds()) == 0)

    def testObjectValuesOneToMany(self):
        """Test objectValues on a ToMany"""
        loc = self.create(self.app, Location, "loc")
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        loc.addRelation("devices", dev)
        loc.addRelation("devices", dev2)
        self.failUnless(len(loc.devices.objectValuesAll()) == 2)
        self.failUnless(dev in loc.devices.objectValuesAll())
        self.failUnless(dev2 in loc.devices.objectValuesAll())
        self.failUnless(len(loc.devices.objectValues()) == 0)

    def testObjectItemsOneToMany(self):
        """Test objectItems on a ToMany"""
        loc = self.create(self.dmd, Location, "loc")
        dev = self.create(self.dmd, Device, "dev")
        dev2 = self.create(self.dmd, Device, "dev2")
        devid = dev.getPrimaryId()
        dev2id = dev2.getPrimaryId()
        loc.addRelation("devices", dev)
        loc.addRelation("devices", dev2)
        self.failUnless(len(loc.devices.objectItemsAll()) == 2)
        self.failUnless((devid, dev) in loc.devices.objectItemsAll())
        self.failUnless((dev2id, dev2) in loc.devices.objectItemsAll())
        self.failUnless(len(loc.devices.objectItems()) == 0)

    def testaddRelationManyToMany(self):
        """Test froming a many to many relationship"""
        dev = self.create(self.app, Device, "dev")
        group = self.create(self.app, Group, "group")
        dev.addRelation("groups", group)
        self.failUnless(group in dev.groups())
        self.failUnless(dev in group.devices())

    def testSetObjectManyToMany(self):
        """Test froming a many to many relationship"""
        dev = self.create(self.app, Device, "dev")
        group = self.create(self.app, Group, "group")
        dev.groups._setObject("group", group)
        self.failUnless(group in dev.groups())
        self.failUnless(dev in group.devices())

    def testaddRelationToManyNone(self):
        """Test adding None to a to many relationship"""
        dev = self.create(self.app, Device, "dev")
        self.failUnlessRaises(
            ZenRelationsError, dev.addRelation, "groups", None
        )

    def testremoveRelationManyToMany(self):
        """Test removing from a to many relationship"""
        dev = self.create(self.app, Device, "dev")
        group = self.create(self.app, Group, "group")
        dev.addRelation("groups", group)
        self.failUnless(group in dev.groups())
        dev.removeRelation("groups", group)
        self.failIf(group in dev.groups())
        self.failIf(dev in group.devices())

    def testremoveRelationManyToMany2(self):
        """Test removing from a to many relationship with two objects"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        group = self.create(self.app, Group, "group")
        group2 = self.create(self.app, Group, "group2")
        dev.addRelation("groups", group)
        dev.addRelation("groups", group2)
        dev2.addRelation("groups", group)
        self.failUnless(len(group2.devices()) == 1)
        self.failUnless(len(group.devices()) == 2)
        dev.removeRelation("groups", group)
        self.failIf(group in dev.groups())
        self.failIf(dev in group.devices())
        self.failUnless(group2 in dev.groups())
        self.failUnless(dev2 in group.devices())

    def testremoveRelationManyToMany4(self):
        """Test removing all from many to many relationship"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        group = self.create(self.app, Group, "group")
        group2 = self.create(self.app, Group, "group2")
        dev.addRelation("groups", group)
        dev.addRelation("groups", group2)
        dev2.addRelation("groups", group)
        self.failUnless(len(group2.devices()) == 1)
        self.failUnless(len(group.devices()) == 2)
        dev.removeRelation("groups")
        self.failUnless(len(dev.groups()) == 0)
        self.failIf(dev in group.devices())
        self.failIf(group2 in dev.groups())
        self.failUnless(dev2 in group.devices())

    def testremoveRelationManyToMany5(self):
        """Test removing non existant object from many to many relationship"""
        dev = self.create(self.app, Device, "dev")
        group = self.create(self.app, Group, "group")
        group2 = self.create(self.app, Group, "group2")
        dev.addRelation("groups", group)
        self.assertRaises(ObjectNotFound, dev.removeRelation, "groups", group2)
        self.failUnless(len(group2.devices()) == 0)
        self.failUnless(len(group.devices()) == 1)
        self.failUnless(dev in group.devices())
        self.failUnless(len(dev.groups()) == 1)
        self.failUnless(group in dev.groups())

    def testDeleteToManyRelationship(self):
        """Test deleteing the to many side of a many to many relationship"""
        dev = self.create(self.app, Device, "dev")
        group = self.create(self.app, Group, "group")
        dev.addRelation("groups", group)
        self.failUnless(group in dev.groups())
        dev._delObject("groups")
        self.failIf(dev in group.devices())
        self.failIf(hasattr(dev, "groups"))

    def testGetObToMany(self):
        dev = self.create(self.app, Device, "dev")
        group = self.create(self.app, Group, "group")
        dev.addRelation("groups", group)
        self.failUnless(group in dev.groups())
        self.failUnless(dev.groups._getOb("group") == group)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(PrimaryPathManagerTest))
    suite.addTest(makeSuite(RelationshipManagerTest))
    suite.addTest(makeSuite(ToOneRelationshipTest))
    suite.addTest(makeSuite(ToManyContRelationshipTest))
    suite.addTest(makeSuite(ToManyRelationshipTest))
    return suite


if __name__ == "__main__":
    framework()
