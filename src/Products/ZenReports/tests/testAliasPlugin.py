##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenModel.tests.RRDTestUtils import addAlias, createTemplate
from Products.ZenReports.AliasPlugin import (
    AliasPlugin,
    Column,
    PythonColumnHandler,
    RRDColumnHandler,
)
from Products.ZenReports.tests.ReportTestUtils import (
    attributeAsRRDValue,
    createTestDevice,
    getComponentIdFromRecord,
    getDeviceIdFromRecord,
    replaceGetRRDValue,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class _TestPlugin(AliasPlugin):
    def __init__(self, columns=[], compositeColumns=[], componentPath=None):
        self._columns = columns
        self._compositeColumns = compositeColumns
        self._componentPath = componentPath

    def getColumns(self):
        return self._columns

    def getCompositeColumns(self):
        return self._compositeColumns

    def getComponentPath(self):
        return self._componentPath


class TestAliasPlugin(BaseTestCase):
    @replaceGetRRDValue(attributeAsRRDValue)
    def testPropertyColumns(self):
        rackSlot = 44
        template = createTemplate(self.dmd, "TestTemplate1")
        dev = createTestDevice(
            self.dmd,
            "TestDevice1",
            dict(zDeviceTemplates=[template.id], rackSlot=rackSlot),
        )
        test1 = _TestPlugin(
            [
                Column("testCol1"),  # NO VALUES
                Column("testCol2", PythonColumnHandler("device.id")),
                Column("testCol3", PythonColumnHandler("device.rackSlot")),
            ]
        )

        records = test1.run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )
        self.assertEquals(1, len(records))
        record = records[0]
        self.assertEquals(record.values["device"], dev)
        self.assertEquals(record.values["testCol1"], None)
        self.assertEquals(record.values["testCol2"], dev.id)
        self.assertEquals(record.values["testCol3"], rackSlot)

    @replaceGetRRDValue(attributeAsRRDValue)
    def testPropertyAndRRDColumns(self):
        rackSlot = 44
        template = createTemplate(self.dmd, "TestTemplate2")
        addAlias(template, "ds1", "dp1", "testAlias1")
        addAlias(template, "ds1", "dp2", "testAlias2")
        dev2 = createTestDevice(
            self.dmd,
            "TestDevice2",
            dict(zDeviceTemplates=[template.id], rackSlot=rackSlot),
        )
        dev3 = createTestDevice(
            self.dmd, "TestDevice3", dict(rackSlot=rackSlot)
        )
        test1 = _TestPlugin(
            [
                Column("testCol1", PythonColumnHandler("device.id")),
                Column("testCol3", PythonColumnHandler("device.rackSlot")),
                Column("testCol2", RRDColumnHandler("testAlias1")),
                Column("testCol4", RRDColumnHandler("testAlias2")),
            ]
        )

        testValue1 = 33
        testValue2 = 66
        dev2.dp1 = testValue1
        dev2.dp2 = testValue2

        records = test1.run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )
        self.assertEquals(2, len(records))
        recordMap = dict(zip(map(getDeviceIdFromRecord, records), records))
        for dev in [dev2, dev3]:
            record = recordMap[dev.id]
            self.assertEquals(dev, record.values["device"])
            self.assertEquals(dev.id, record.values["testCol1"])
            self.assertEquals(rackSlot, record.values["testCol3"])

        record2 = recordMap[dev2.id]
        self.assertEquals(testValue1, record2.values["testCol2"])
        self.assertEquals(testValue2, record2.values["testCol4"])
        record3 = recordMap[dev3.id]
        self.assertEquals(None, record3.values["testCol2"])
        self.assertEquals(None, record3.values["testCol4"])

    @replaceGetRRDValue(attributeAsRRDValue)
    def testComponentReport(self):
        rackSlot = 88
        interfaceType = "testinterfacetype"
        template = createTemplate(self.dmd, interfaceType)
        addAlias(template, "ds1", "dp1", "testAlias1")
        addAlias(template, "ds1", "dp2", "testAlias2")

        dev4 = createTestDevice(
            self.dmd,
            "TestDevice2",
            dict(zDeviceTemplates=[template.id], rackSlot=rackSlot),
        )
        dev4.os.addIpInterface("testComponent1", False)
        testComponent1 = dev4.os.interfaces._getOb("testComponent1")
        testComponent1.type = interfaceType

        dev5 = createTestDevice(
            self.dmd, "TestDevice3", dict(rackSlot=rackSlot)
        )
        dev5.os.addIpInterface("testComponent2", False)
        testComponent2 = dev5.os.interfaces._getOb("testComponent2")
        testComponent2.type = "wronginterfacetype"

        test3 = _TestPlugin(
            [
                Column("testCol1", PythonColumnHandler("component.id")),
                Column("testCol3", PythonColumnHandler("device.rackSlot")),
                Column("testCol2", RRDColumnHandler("testAlias1")),
                Column("testCol4", RRDColumnHandler("testAlias2")),
            ],
            componentPath="os/interfaces",
        )

        testValue1 = 55
        testValue2 = 77
        testComponent1.dp1 = testValue1
        testComponent1.dp2 = testValue2

        records = test3.run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )
        self.assertEquals(2, len(records))
        recordMap = dict(zip(map(getComponentIdFromRecord, records), records))
        for component in [testComponent1, testComponent2]:
            record = recordMap[component.id]
            self.assertEquals(component.device(), record.values["device"])
            self.assertEquals(component, record.values["component"])
            self.assertEquals(component.id, record.values["testCol1"])
            self.assertEquals(rackSlot, record.values["testCol3"])

        record1 = recordMap[testComponent1.id]
        self.assertEquals(testValue1, record1.values["testCol2"])
        self.assertEquals(testValue2, record1.values["testCol4"])
        record2 = recordMap[testComponent2.id]
        self.assertEquals(None, record2.values["testCol2"])
        self.assertEquals(None, record2.values["testCol4"])

    @replaceGetRRDValue(attributeAsRRDValue)
    def testCompositeColumns(self):
        # import pydevd;pydevd.settrace()
        rackSlot = 44
        template = createTemplate(self.dmd, "TestTemplate3")
        addAlias(template, "ds1", "dp1", "testAlias5")
        addAlias(template, "ds1", "dp2", "testAlias6")
        dev5 = createTestDevice(
            self.dmd,
            "TestDevice5",
            dict(zDeviceTemplates=[template.id], rackSlot=rackSlot),
        )
        dev6 = createTestDevice(
            self.dmd, "TestDevice6", dict(rackSlot=rackSlot)
        )
        test3 = _TestPlugin(
            [
                Column("testCol1", PythonColumnHandler("device.id")),
                Column("testCol3", PythonColumnHandler("device.rackSlot")),
                Column("testCol2", RRDColumnHandler("testAlias5")),
                Column("testCol4", RRDColumnHandler("testAlias6")),
            ],
            [
                Column(
                    "testCol5",
                    PythonColumnHandler(
                        "testCol2 and testCol4 and "
                        "( testCol2 + testCol4 ) / 10"
                    ),
                )
            ],
        )

        testValue1 = 120
        testValue2 = 240
        dev5.dp1 = testValue1
        dev5.dp2 = testValue2

        records = test3.run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )
        self.assertEquals(2, len(records))
        recordMap = dict(zip(map(getDeviceIdFromRecord, records), records))
        for dev in [dev5, dev6]:
            record = recordMap[dev.id]
            self.assertEquals(dev, record.values["device"])
            self.assertEquals(dev.id, record.values["testCol1"])
            self.assertEquals(rackSlot, record.values["testCol3"])

        record5 = recordMap[dev5.id]
        self.assertEquals(testValue1, record5.values["testCol2"])
        self.assertEquals(testValue2, record5.values["testCol4"])
        self.assertEquals(
            (testValue1 + testValue2) / 10, record5.values["testCol5"]
        )
        record6 = recordMap[dev6.id]
        self.assertEquals(None, record6.values["testCol2"])
        self.assertEquals(None, record6.values["testCol4"])
        self.assert_("testCol6" not in record6.values.keys())


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestAliasPlugin))
    return suite
