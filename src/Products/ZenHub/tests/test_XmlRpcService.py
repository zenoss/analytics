from unittest import TestCase
from mock import Mock, patch, MagicMock

from Products.ZenHub.XmlRpcService import (
    XmlRpcService,
)

PATH = {"src": "Products.ZenHub.XmlRpcService"}


class XmlRpcServiceTest(TestCase):
    def setUp(t):
        t.dmd = Mock(
            name="dmd",
            spec_set=["ZenEventManager", "Devices", "findDevice", "Monitors"],
        )
        t.zem = Mock(
            name="ZenEventManager", spec_set=["sendEvent", "sendEvents"]
        )
        t.dmd.ZenEventManager = t.zem
        t.xrs = XmlRpcService(t.dmd)

        t.data = Mock(name="data", spec_set=[])

    def test___init_(t):
        t.assertEqual(t.xrs.dmd, t.dmd)
        t.assertEqual(t.xrs.zem, t.dmd.ZenEventManager)

    def test_xmlrpc_sendEvent(t):
        result = Mock(name="result", spec_set=[])
        t.zem.sendEvent.return_value = result

        ret = t.xrs.xmlrpc_sendEvent(t.data)

        t.zem.sendEvent.assert_called_with(t.data)
        t.assertEqual(ret, result)

    def test_xmlrpc_sendEvent_None_result(t):
        result = None
        t.zem.sendEvent.return_value = result

        ret = t.xrs.xmlrpc_sendEvent(t.data)

        t.zem.sendEvent.assert_called_with(t.data)
        t.assertEqual(ret, "none")

    def test_xmlrpc_sendEvents(t):
        ret = t.xrs.xmlrpc_sendEvents(t.data)
        t.zem.sendEvents.assert_called_with(t.data)
        t.assertEqual(ret, t.xrs.zem.sendEvents.return_value)

    @patch("{src}.getFacade".format(**PATH), autospec=True)
    def test_xmlrpc_getDevicePingIssues(t, getFacade):
        ret = t.xrs.xmlrpc_getDevicePingIssues(t.data)

        getFacade.assert_called_with("zep")
        zep = getFacade.return_value
        t.assertEqual(ret, zep.getDevicePingIssues.return_value)

    def test_xmlrpc_getDeviceWinInfo(t):
        args = ["arg_0", "arg_1", "arg_2"]
        ret = t.xrs.xmlrpc_getDeviceWinInfo(*args)

        getDeviceWinInfo = t.dmd.Devices.Server.Windows.getDeviceWinInfo
        getDeviceWinInfo.assert_called_with(*args)
        t.assertEqual(ret, getDeviceWinInfo.return_value)

    def test_xmlrpc_getWinServices(t):
        args = ["arg_0", "arg_1", "arg_2"]
        ret = t.xrs.xmlrpc_getWinServices(*args)

        getWinServices = t.dmd.Devices.Server.Windows.getWinServices
        getWinServices.assert_called_with(*args)
        t.assertEqual(ret, getWinServices.return_value)

    @patch("{src}.ApplyDataMap".format(**PATH), autospec=True)
    def test_xmlrpc_applyDataMap(t, ApplyDataMap):
        devName = "device_name"
        datamap = Mock(name="datamap", spec_set=[])
        relname = "relname"
        compname = "compname"
        modname = "modname"

        t.xrs.xmlrpc_applyDataMap(devName, datamap, relname, compname, modname)

        t.dmd.findDevice.assert_called_with(devName)
        dev = t.dmd.findDevice.return_value
        adm = ApplyDataMap.return_value
        adm.applyDataMap.assert_called_with(
            dev, datamap, relname, compname, modname
        )

    def test_xmlrpc_getConfigs(t):
        """all of this getConfigs logic needs to be moved out of the
        rpc service, and into a more appropriate module

        We also have to test the internally defined toDict function
        current code will not even run, and will throw a TypeError
        due to isinstance(val, XmlRpcService.PRIMITIVES):
        TypeError: isinstance() arg 2 must be a class, type, or tuple of classes and types

        no other code calls this method,and it can be safely removed.
        """
        conf = Mock(name="monitor", spec_set=["devices"])
        t.dmd.Monitors.Performance.monitor_name = conf

        devices = [
            Mock(name="device_%s" % i, spec_set=["primaryAq"])
            for i in range(2)
        ]
        conf.devices.return_value = devices
        for device in devices:
            primaryAq = Mock(name="primaryAq", spec_set=["getRRDTemplates"])
            device.primaryAq.return_value = primaryAq
            templates = [
                Mock(name="template_%s" % i, spec_set=["getRRDDataSources"])
                for i in range(2)
            ]
            primaryAq.getRRDTemplates.return_value = templates
            for template in templates:
                data_sources = [
                    MagicMock(
                        name="data_source_a",
                        spec_set=["sourcetype", "datapoints"],
                        sourcetype="data_source_type",
                    ),
                    MagicMock(
                        name="data_source_b",
                        spec_set=["sourcetype", "datapoints"],
                        sourcetype="ignored",
                    ),
                    MagicMock(
                        name="data_source_b",
                        spec_set=["sourcetype", "datapoints"],
                        sourcetype="data_source_type",
                    ),
                ]
                template.getRRDDataSources.return_value = data_sources

        # We also have to test the internally defined toDict function
        # current code will not even run, and will throw a TypeError
        # due to isinstance(val, XmlRpcService.PRIMITIVES):
        # TypeError: isinstance() arg 2 must be a class, type, or tuple of classes and types
        with t.assertRaises(TypeError):
            ret = t.xrs.xmlrpc_getConfigs(
                monitor="monitor_name", dstype="data_source_type"
            )
        # t.assertEqual(ret, 'something')

    def test_xmlrpc_writeRRD(t):
        # Deprecated
        with t.assertRaises(NotImplementedError):
            t.xrs.xmlrpc_writeRRD(
                "devId", "compType", "compId", "dpName", "value"
            )

    def test_xmlrpc_getPerformanceConfig(t):
        conf = Mock(
            name="monitor",
            configCycleInterval="configCycleInterval_value",
            eventlogCycleInterval="eventlogCycleInterval_value",
            winCycleInterval="winCycleInterval_value",
            statusCycleInterval="statusCycleInterval_value",
        )
        t.dmd.Monitors.Performance.monitor_name = conf
        ret = t.xrs.xmlrpc_getPerformanceConfig("monitor_name")
        t.assertEqual(
            ret,
            {
                "configCycleInterval": "configCycleInterval_value",
                "eventlogCycleInterval": "eventlogCycleInterval_value",
                "winCycleInterval": "winCycleInterval_value",
                "statusCycleInterval": "statusCycleInterval_value",
            },
        )
