# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.ZenModel.Device import Device
from Products.DataCollector.plugins.DataMaps import RelationshipMap
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class _dev(object):
    id = "mydevid"

    def device(self):
        return self


class _obj(object):
    a = None
    b = None
    c = None
    id = "myid"
    _device = None
    _dummy = None
    zCollectorDecoding = "latin-1"

    def device(self):
        if not self._device:
            self._device = _dev()
        return self._device

    def _p_deactivate(self):
        pass

    _p_changed = False


class ApplyDataMapTest(BaseTestCase):
    def afterSetUp(self):
        super(ApplyDataMapTest, self).afterSetUp()
        self.adm = ApplyDataMap()

    def test_applyDataMap_relmap(self):
        datamap = RelationshipMap()
        device = Device(id="test_device")
        device.dmd = self.dmd

        self.adm.applyDataMap(
            device, datamap, datamap.relname, datamap.compname
        )

    def test_applyDataMap_relmapException(self):
        """test_applyDataMap_exception is mostly the same as test_applyDataMap_relmap
        - difference #1: compname is commented out
        - difference #2: with self.assertRaises(AttributeError) is added
        """
        dmd = self.dmd

        class datamap(list):
            # compname = "a/b"
            relname = "c"

        class Device(object):
            def deviceClass(self):
                return dmd.Devices

            class dmd:
                """Used for faking sync()"""

                class _p_jar:
                    @staticmethod
                    def sync():
                        pass

            def getObjByPath(self, path):
                return reduce(getattr, path.split("/"), self)

            class a:
                class b:
                    class c:
                        """The relationship to populate"""

                        @staticmethod
                        def objectIdsAll():
                            """returns the list of object ids
                            in this relationship"""
                            return []

        with self.assertRaises(AttributeError) as theException:
            self.adm.applyDataMap(
                Device(), datamap(), datamap.relname, datamap.compname
            )

        self.assertEqual(
            theException.exception.message,
            "type object 'datamap' has no attribute 'compname'",
        )

    def testNoChangeAllComponentsLocked(self):
        device = self.dmd.Devices.createInstance("testDevice")
        # Create an IP interface
        device.os.addIpInterface("eth0", False)
        iface = device.os.interfaces._getOb("eth0")
        iface.lockFromDeletion()

        # Apply a RelMap with no interfaces
        relmap = RelationshipMap(
            "interfaces", "os", "Products.ZenModel.IpInterface"
        )
        self.assertFalse(self.adm._applyDataMap(device, relmap))

        self.assertEquals(1, len(device.os.interfaces))


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(ApplyDataMapTest))
    return suite
