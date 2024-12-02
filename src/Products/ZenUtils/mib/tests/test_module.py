##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase

from Acquisition import aq_base

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.mib import (
    MibOrganizerPath, getMibModuleMap, ModuleManager
)


class TestMibOrganizerPath(TestCase):

    def test_no_path(self):
        path = MibOrganizerPath()
        self.assertEqual(path.path, "/zport/dmd/Mibs")
        self.assertEqual(path.relative_path, "/")

    def test_full_path_root_organizer(self):
        path = MibOrganizerPath("/zport/dmd/Mibs")
        self.assertEqual(path.path, "/zport/dmd/Mibs")
        self.assertEqual(path.relative_path, "/")

    def test_relative_path_root_organizer(self):
        path = MibOrganizerPath("/")
        self.assertEqual(path.path, "/zport/dmd/Mibs")
        self.assertEqual(path.relative_path, "/")

    def test_full_path_sub_organizer(self):
        path = MibOrganizerPath("/zport/dmd/Mibs/MyMibs")
        self.assertEqual(path.path, "/zport/dmd/Mibs/MyMibs")
        self.assertEqual(path.relative_path, "/MyMibs")

    def test_relative_path_sub_organizer(self):
        path = MibOrganizerPath("/MyMibs")
        self.assertEqual(path.path, "/zport/dmd/Mibs/MyMibs")
        self.assertEqual(path.relative_path, "/MyMibs")

    def test_relative_path_sub_organizer_no_root(self):
        path = MibOrganizerPath("MyMibs")
        self.assertEqual(path.path, "/zport/dmd/Mibs/MyMibs")
        self.assertEqual(path.relative_path, "/MyMibs")


class TestMibModuleMap(BaseTestCase):

    def test_no_modules(self):
        registry = getMibModuleMap(self.dmd)
        self.assertEqual(len(registry), 0)

    def test_one_module(self):
        self.dmd.Mibs.createMibModule("TEST-MIB-01", "/")

        registry = getMibModuleMap(self.dmd)
        self.assertEqual(len(registry), 1)

        path = registry.get("TEST-MIB-01")
        self.assertIsNotNone(path)
        self.assertIsInstance(path, MibOrganizerPath)
        self.assertEqual(path.path, "/zport/dmd/Mibs")

    def test_n_modules(self):
        self.dmd.Mibs.createMibModule("TEST-MIB-01", "/")
        self.dmd.Mibs.createMibModule("TEST-MIB-02", "/")

        registry = getMibModuleMap(self.dmd)
        self.assertEqual(len(registry), 2)

        path = registry.get("TEST-MIB-01")
        self.assertIsNotNone(path)
        self.assertIsInstance(path, MibOrganizerPath)
        self.assertEqual(path.path, "/zport/dmd/Mibs")

        path = registry.get("TEST-MIB-02")
        self.assertIsNotNone(path)
        self.assertIsInstance(path, MibOrganizerPath)
        self.assertEqual(path.path, "/zport/dmd/Mibs")

    def test_module_in_suborganizer(self):
        self.dmd.Mibs.createOrganizer("MyMibs")
        self.dmd.Mibs.createMibModule("TEST-MIB-01", "/MyMibs")

        registry = getMibModuleMap(self.dmd)
        self.assertEqual(len(registry), 1)

        path = registry.get("TEST-MIB-01")
        self.assertIsNotNone(path)
        self.assertIsInstance(path, MibOrganizerPath)
        self.assertEqual(path.path, "/zport/dmd/Mibs/MyMibs")

    def test_modules_in_various_places(self):
        self.dmd.Mibs.createMibModule("TEST-MIB-01", "/")
        self.dmd.Mibs.createOrganizer("MyMibs")
        self.dmd.Mibs.createMibModule("TEST-MIB-02", "/MyMibs")

        registry = getMibModuleMap(self.dmd)
        self.assertEqual(len(registry), 2)

        path = registry.get("TEST-MIB-01")
        self.assertIsNotNone(path)
        self.assertIsInstance(path, MibOrganizerPath)
        self.assertEqual(path.path, "/zport/dmd/Mibs")

        path = registry.get("TEST-MIB-02")
        self.assertIsNotNone(path)
        self.assertIsInstance(path, MibOrganizerPath)
        self.assertEqual(path.path, "/zport/dmd/Mibs/MyMibs")


class TestModuleManager(BaseTestCase):

    def test_no_existing_module(self):
        module = {
            "moduleName": "TEST-MIB-01",
            "TEST-MIB-01": {
                "language": "SMIv2",
                "contact": "Some\nContact",
                "description": "Testable"
            }
        }
        organizerPath = MibOrganizerPath()

        mm = ModuleManager(self.dmd, {})
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertIsNotNone(mod)
        self.assertEqual(mod.getModuleName(), "TEST-MIB-01")
        self.assertEqual(getattr(mod, "language", None), "SMIv2")
        self.assertEqual(getattr(mod, "contact", None), "Some\nContact")
        self.assertEqual(getattr(mod, "description", None), "Testable")

    def test_existing_module(self):
        expected_mod = self.dmd.Mibs.createMibModule("TEST-MIB-01", "/")
        expected_mod.language = "SMIv1"
        expected_mod.contact = "The Contact"
        expected_mod.description = "Original"

        module = {
            "moduleName": "TEST-MIB-01",
            "TEST-MIB-01": {
                "language": "SMIv2",
                "contact": "Some\nContact",
                "description": "Testable"
            }
        }
        organizerPath = MibOrganizerPath()

        registry = {
            "TEST-MIB-01": MibOrganizerPath("/")
        }
        mm = ModuleManager(self.dmd, registry)
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertIsNotNone(mod)
        self.assertIs(aq_base(mod), aq_base(expected_mod))
        self.assertEqual(mod.getModuleName(), "TEST-MIB-01")
        self.assertEqual(getattr(mod, "language", None), "SMIv2")
        self.assertEqual(getattr(mod, "contact", None), "Some\nContact")
        self.assertEqual(getattr(mod, "description", None), "Testable")

    def test_existing_module_in_suborganizer(self):
        self.dmd.Mibs.createOrganizer("MyMibs")
        expected_mod = self.dmd.Mibs.createMibModule("TEST-MIB-01", "/MyMibs")
        expected_mod.language = "SMIv1"
        expected_mod.contact = "The Contact"
        expected_mod.description = "Original"

        module = {
            "moduleName": "TEST-MIB-01",
            "TEST-MIB-01": {
                "language": "SMIv2",
                "contact": "Some\nContact",
                "description": "Testable"
            }
        }
        organizerPath = MibOrganizerPath()

        registry = {
            "TEST-MIB-01": MibOrganizerPath("/MyMibs")
        }
        mm = ModuleManager(self.dmd, registry)
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertIsNone(mod)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/MyMibs/mibs/TEST-MIB-01", None
        )
        self.assertIsNotNone(mod)
        self.assertIs(aq_base(mod), aq_base(expected_mod))
        self.assertEqual(mod.getModuleName(), "TEST-MIB-01")
        self.assertEqual(getattr(mod, "language", None), "SMIv2")
        self.assertEqual(getattr(mod, "contact", None), "Some\nContact")
        self.assertEqual(getattr(mod, "description", None), "Testable")

    def test_partially_update_existing_module_attributes(self):
        expected_mod = self.dmd.Mibs.createMibModule("TEST-MIB-01", "/")
        expected_mod.language = "SMIv1"
        expected_mod.contact = "The Contact"
        expected_mod.description = "Original"

        module = {
            "moduleName": "TEST-MIB-01",
            "TEST-MIB-01": {
                "language": "SMIv2",
                "contact": "Some\nContact",
            }
        }
        organizerPath = MibOrganizerPath()

        registry = {
            "TEST-MIB-01": MibOrganizerPath("/")
        }
        mm = ModuleManager(self.dmd, registry)
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertIsNotNone(mod)
        self.assertIs(aq_base(mod), aq_base(expected_mod))
        self.assertEqual(mod.getModuleName(), "TEST-MIB-01")
        self.assertEqual(getattr(mod, "language", None), "SMIv2")
        self.assertEqual(getattr(mod, "contact", None), "Some\nContact")
        self.assertEqual(getattr(mod, "description", None), "Original")

    def test_add_node(self):
        module = {
            "moduleName": "TEST-MIB-01",
            "nodes": {
                "test01": {
                    "nodetype": "node",
                    "moduleName": "TEST-MIB-01",
                    "oid": "1.3.6.1.6.3.19",
                    "status": "current"
                }
            }
        }
        organizerPath = MibOrganizerPath()

        mm = ModuleManager(self.dmd, {})
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertEqual(mod.nodeCount(), 1)
        self.assertEqual(mod.notificationCount(), 0)
        node = next(iter(mod.nodes()), None)
        self.assertEqual(node.id, "test01")
        self.assertEqual(node.moduleName, "TEST-MIB-01")
        self.assertEqual(node.nodetype, "node")
        self.assertEqual(node.oid, "1.3.6.1.6.3.19")
        self.assertEqual(node.status, "current")
        self.assertEqual(node.description, "")

    def test_add_notification(self):
        module = {
            "moduleName": "TEST-MIB-01",
            "notifications": {
                "trap01": {
                    "nodetype": "notification",
                    "moduleName": "TEST-MIB-01",
                    "oid": "1.3.6.1.6.3.19",
                    "status": "current"
                }
            }
        }
        organizerPath = MibOrganizerPath()

        mm = ModuleManager(self.dmd, {})
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertEqual(mod.nodeCount(), 0)
        self.assertEqual(mod.notificationCount(), 1)
        node = next(iter(mod.notifications()), None)
        self.assertEqual(node.id, "trap01")
        self.assertEqual(node.moduleName, "TEST-MIB-01")
        self.assertEqual(node.nodetype, "notification")
        self.assertEqual(node.oid, "1.3.6.1.6.3.19")
        self.assertEqual(node.status, "current")
        self.assertEqual(node.description, "")

    def test_add_one_node_and_notification(self):
        module = {
            "moduleName": "TEST-MIB-01",
            "nodes": {
                "test01": {
                    "nodetype": "node",
                    "moduleName": "TEST-MIB-01",
                    "oid": "1.3.6.1.6.3.19",
                    "status": "current"
                }
            },
            "notifications": {
                "trap01": {
                    "nodetype": "notification",
                    "moduleName": "TEST-MIB-01",
                    "oid": "1.3.6.1.1.4.5",
                    "status": "current"
                }
            }
        }
        organizerPath = MibOrganizerPath()

        mm = ModuleManager(self.dmd, {})
        mm.add(module, organizerPath)

        mod = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/TEST-MIB-01", None
        )
        self.assertEqual(mod.nodeCount(), 1)
        self.assertEqual(mod.notificationCount(), 1)
        node = next(iter(mod.nodes()), None)
        self.assertEqual(node.id, "test01")
        self.assertEqual(node.oid, "1.3.6.1.6.3.19")
        node = next(iter(mod.notifications()), None)
        self.assertEqual(node.id, "trap01")
        self.assertEqual(node.oid, "1.3.6.1.1.4.5")
