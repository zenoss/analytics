##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import copy
import logging
import os

from cPickle import load

from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.InterfaceAliasMap import (
    InterfaceAliasMap,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class TestInterfaceAliasMap(BaseTestCase):
    def afterSetUp(self):
        super(TestInterfaceAliasMap, self).afterSetUp()
        self.adm = ApplyDataMap()
        self.iamap = InterfaceAliasMap()
        self.device = self.dmd.Devices.createInstance("testDevice")

    def testCisco3560(self):
        pickle = open(
            "%s/data/InterfaceAliasMap_cisco3560.pickle"
            % os.path.dirname(__file__),
            "rb",
        )
        results = load(pickle)
        pickle.close()

        # Verify that the modeler plugin processes the data properly.
        relmap = self.iamap.process(self.device, results, log)
        relmap_orig = copy.deepcopy(relmap)

        self.assertEquals(relmap.compname, "os")
        self.assertEquals(relmap.relname, "interfaces")
        self.assertEquals(len(relmap.maps), 58)
        om = relmap.maps[0]
        self.assertEquals(om.id, "Vl1")
        self.assertEquals(om.description, "Description of Vlan1")

        # Verify that the data made it into the model properly.
        self.adm.applyDataMap(self.device, relmap)

        iface = self.device.os.interfaces.Vl1
        self.assertEquals(iface.id, "Vl1")
        self.assertEquals(iface.description, "Description of Vlan1")

        # print(
        #    '\n========================================\n'
        #    '    UPDATE MODEL'
        #    '\n========================================\n'
        # )
        # clear old directives
        relmap = relmap_orig
        om = relmap.maps[0]
        # update the device
        om.description = "New Description of Vlan1"
        om._do_not_include = "ignore me!"
        self.assertEquals(om.description, "New Description of Vlan1")
        self.adm.applyDataMap(self.device, relmap)
        iface = self.device.os.interfaces.Vl1
        self.assertEquals(iface.id, "Vl1")
        self.assertEquals(iface.description, "New Description of Vlan1")
        self.assertFalse(hasattr(iface, "_do_not_include"))


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestInterfaceAliasMap))
    return suite
