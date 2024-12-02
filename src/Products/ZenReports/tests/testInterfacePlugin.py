##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenModel.tests.RRDTestUtils import addAlias, createTemplate
from Products.ZenReports.plugins.interface import interface
from Products.ZenReports.tests.ReportTestUtils import (
    assertRecordIsCorrect,
    attributeAsRRDValue,
    createTestDevice,
    getComponentIdFromRecord,
    replaceGetRRDValue,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase


def createInterface(
    device, id, speed, inputOctets, outputOctets, properties={}
):
    device.os.addIpInterface(id, False)
    interface = device.os.interfaces._getOb(id)
    interface.speed = speed
    interface.adminStatus = 1
    interface.ifInputOctets_ifInputOctets = inputOctets
    interface.ifOutputOctets_ifOutputOctets = outputOctets
    for key, value in properties.iteritems():
        setattr(interface, key, value)
    return interface


def assertInterfaceRowIsCorrect(
    test,
    records,
    device,
    interface,
    testSpeed,
    testInputOctets,
    testOutputOctets,
):
    record = dict(zip(map(getComponentIdFromRecord, records), records))[
        interface.id
    ]
    testTotal = testInputOctets + testOutputOctets
    testPercentUsed = long(testTotal) * 8 * 100.0 / testSpeed
    assertRecordIsCorrect(
        test,
        record,
        dict(
            speed=interface.speed,
            input=testInputOctets,
            output=testOutputOctets,
            total=testTotal,
            percentUsed=testPercentUsed,
        ),
    )


INTERFACE_TEMPLATE_ID = "ethernetCsmacd"


def createInterfaceTemplate(dmd):
    template = createTemplate(
        dmd,
        INTERFACE_TEMPLATE_ID,
        {
            "ds1": [
                "ifOutputOctets_ifOutputOctets",
            ],
            "ds2": [
                "ifInputOctets_ifInputOctets",
            ],
        },
    )
    addAlias(
        template, "ds1", "ifOutputOctets_ifOutputOctets", "outputOctets__bytes"
    )
    addAlias(
        template, "ds2", "ifInputOctets_ifInputOctets", "inputOctets__bytes"
    )
    return template


def createTestDeviceWithInterfaceTemplateBound(dmd, deviceId):
    device = createTestDevice(
        dmd,
        deviceId,
        {
            "zDeviceTemplates": [
                INTERFACE_TEMPLATE_ID,
            ]
        },
    )
    return device


class TestInterfacePlugin(BaseTestCase):
    @replaceGetRRDValue(attributeAsRRDValue)
    def testNoValues(self):
        template = createTemplate(self.dmd, "TestTemplate1")
        createTestDevice(
            self.dmd, "TestDevice1", dict(zDeviceTemplates=[template.id])
        )

        records = interface().run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )
        self.assertEquals(0, len(records))

    @replaceGetRRDValue(attributeAsRRDValue)
    def testOneValue(self):
        testSpeed = 100
        testInputOctets = 5
        testOutputOctets = 20
        createInterfaceTemplate(self.dmd)
        device = createTestDeviceWithInterfaceTemplateBound(
            self.dmd, "TestDevice2"
        )
        interface1 = createInterface(
            device,
            "TestFilesystem2",
            testSpeed,
            testInputOctets,
            testOutputOctets,
        )

        plugin = interface()
        records = plugin.run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )

        self.assertEquals(1, len(records))
        assertInterfaceRowIsCorrect(
            self,
            records,
            device,
            interface1,
            testSpeed,
            testInputOctets,
            testOutputOctets,
        )

    @replaceGetRRDValue(attributeAsRRDValue)
    def testMultipleValues(self):
        # import pydevd;pydevd.settrace()
        testProperties = [
            (
                "testdevice3",
                [("testfs3_1", 100, 20, 15), ("testfs3_2", 50, 100, 98)],
            ),
            ("testdevice4", [("testfs4_1", 300, 20, 15)]),
            (
                "testdevice5",
                [
                    ("testfs5_1", 100, 20, 15),
                    ("testfs5_2", 30, 20, 15),
                    ("testfs5_3", 160, 20, 15),
                ],
            ),
            ("testdevice6", []),
        ]
        createInterfaceTemplate(self.dmd)
        interfaceCount = 0
        testObjects = {}
        for propertySet in testProperties:
            device = createTestDeviceWithInterfaceTemplateBound(
                self.dmd, propertySet[0]
            )
            testInterfaces = []
            for interfaceProperties in propertySet[1]:
                interfaceN = createInterface(
                    device,
                    interfaceProperties[0],
                    interfaceProperties[1],
                    interfaceProperties[2],
                    interfaceProperties[3],
                )
                testInterfaces.append(interfaceN)
                interfaceCount += 1
            testObjects[device] = testInterfaces

        plugin = interface()
        records = plugin.run(
            self.dmd, {"deviceClass": "/Devices/Server", "generate": True}
        )

        self.assertEquals(interfaceCount, len(records))
        for device, interfaceObjects in testObjects.iteritems():
            for interfaceObject in interfaceObjects:
                assertInterfaceRowIsCorrect(
                    self,
                    records,
                    device,
                    interfaceObject,
                    interfaceObject.speed,
                    interfaceObject.ifInputOctets_ifInputOctets,
                    interfaceObject.ifOutputOctets_ifOutputOctets,
                )


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestInterfacePlugin))
    return suite
