##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.ZenStatus import TraceHop
from Products.ZenStatus.SimpleCorrelator import simpleCorrelator
from Products.ZenTestCase.BaseTestCase import BaseTestCase

LOG = logging.getLogger("zenstatus.tests")


def noOpYield():
    return None


devices = (
    {
        "id": "router_0",
        "trace": ("collector_0_ip", "router_0_ip"),
        "iface": "eth0",
        "connectedIps": (("router_0_ip_1", "eth1"), ("router_0_ip_2", "eth2")),
    },
    {
        "id": "router_1",
        "trace": ("collector_0_ip", "router_0_ip", "router_1_ip"),
        "iface": "eth0",
        "connectedIps": (("router_1_ip_1", "eth1"), ("router_1_ip_2", "eth2")),
    },
    {
        "id": "device_0",
        "trace": (
            "collector_0_ip",
            "router_0_ip",
            "router_1_ip",
            "device_0_ip",
        ),
        "iface": "eth0",
        "connectedIps": None,
    },
    {
        "id": "device_1",
        "trace": (
            "collector_0_ip",
            "router_0_ip",
            "router_1_ip_1",
            "device_1_ip",
        ),
        "iface": "eth0",
        "connectedIps": None,
    },
    {
        "id": "device_2",
        "trace": (
            "collector_0_ip",
            "router_0_ip",
            "router_1_ip_2",
            "device_2_ip",
        ),
        "iface": "eth0",
        "connectedIps": None,
    },
    {
        "id": "device_3",
        "trace": ("collector_0_ip", "router_0_ip", "device_3_ip"),
        "iface": "eth0",
        "connectedIps": None,
    },
    {
        "id": "device_4",
        "trace": ("collector_0_ip", "router_0_ip_1", "device_4_ip"),
        "iface": "eth0",
        "connectedIps": None,
    },
    {
        "id": "device_5",
        "trace": ("collector_0_ip", "router_0_ip_2", "device_5_ip"),
        "iface": "eth0",
        "connectedIps": None,
    },
    {
        "id": "device_6",
        "trace": ("collector_0_ip", "router_x", "device_6"),
        "iface": "eth0",
        "connectedIps": None,
    },
)

#  Device Topology described above
#
#  collector0-+-->router0
#             |       ip-+----------->router1
#             |          |               ip------------->device_0
#             |          |               ip_1----------->device_1
#             |          |               ip_2----------->device_2
#             |          |
#             |          +----------->device3
#             |
#             |       ip_1----------->device4
#             |
#             |       ip_2----------->device5
#             |
#             +-->router_x----------->device6


class MockConfig(object):
    def __init__(self, id, ip):
        self.id = id
        self.configId = id
        self.ip = ip


class MockPingTask(object):
    def __init__(
        self, id, trace=None, eventQueue=[], connectedIps=(), iface=""
    ):
        self._eventQueue = eventQueue
        self.isUp = True
        self.delayedIsUp = True
        self.trace = [TraceHop(ip=ip, rtt=1) for ip in trace]
        ip = trace[-1]
        config = MockConfig(id, ip)
        self.config = config
        self.config.iface = iface
        self.configId = id
        self._device = config
        self._device.connectedIps = connectedIps

    def sendPingDown(self, *args, **kwargs):
        evt = {
            "id": self.config.id,
            "up": False,
        }
        evt.update(kwargs)
        self._eventQueue.append(evt)


def makeMockPingTaskFromMap(device, eventQueue):
    return MockPingTask(
        device["id"],
        trace=device["trace"],
        eventQueue=eventQueue,
        iface=device["iface"],
        connectedIps=device["connectedIps"],
    )


class TestSimpleCorrelator(BaseTestCase):
    def setUp(self):
        pass

    def _new_tasks(self):
        self._events = []
        return {
            d["id"]: makeMockPingTaskFromMap(d, self._events) for d in devices
        }

    def testAllUp(self):
        tasks = self._new_tasks()
        for x in simpleCorrelator(
            tasks, connected_ips=True, reactorYield=noOpYield
        ):
            pass
        eventCount = len(self._events)
        self.assertEqual(
            eventCount,
            0,
            "All devices should be up, but got %d events" % eventCount,
        )

    def testEdgeDown(self):
        tasks = self._new_tasks()
        tasks["device_6"].isUp = False
        tasks["device_6"].delayedIsUp = False

        # exercise correlator
        for x in simpleCorrelator(
            tasks, connected_ips=True, reactorYield=noOpYield
        ):
            pass

        # should have 1 down event
        eventCount = len(self._events)
        self.assertEqual(
            eventCount,
            1,
            "One device should be down, but got %d events" % eventCount,
        )

        # make sure we get the event we expect
        expectedEvent = {"id": "device_6", "up": False}
        self.assertDictEqual(expectedEvent, self._events[0])

    def testRouter1DownNoConnectedIps(self):
        tasks = self._new_tasks()
        for devId in ("device_0", "device_1", "device_2", "router_1"):
            task = tasks[devId]
            task.isUp = False
            task.delayedIsUp = False

        # exercise correlator
        for x in simpleCorrelator(
            tasks, connected_ips=False, reactorYield=noOpYield
        ):
            pass

        # should have 4 down events
        eventCount = len(self._events)
        self.assertEqual(
            eventCount,
            4,
            "4 devices should be down, but got %d events" % eventCount,
        )

        # make sure we get the events we expect
        expectedEvents = {}
        expectedEvents["device_0"] = {
            "rootcause.componentId": "eth0",
            "rootcause.message": (
                "IP 'router_1_ip' on interface 'eth0' is connected to "
                "device 'router_1' and is also in the traceroute for "
                "monitored ip 'device_0_ip' on device 'device_0'"
            ),
            "rootcause.componentIP": "router_1_ip",
            "rootcause.deviceId": "router_1",
            "suppressed": True,
            "id": "device_0",
            "up": False,
        }
        expectedEvents["device_1"] = {"id": "device_1", "up": False}
        expectedEvents["device_2"] = {"id": "device_2", "up": False}
        expectedEvents["router_1"] = {"id": "router_1", "up": False}

        while len(self._events):
            actualEvent = self._events.pop()
            expectedEvent = expectedEvents.get(actualEvent["id"], None)
            self.assertIsNotNone(
                expectedEvent, "Unexpected event generated: %r" % actualEvent
            )
            self.assertDictEqual(actualEvent, expectedEvent)

    def testRouter1DownConnectedIps(self):
        tasks = self._new_tasks()
        for devId in ("device_0", "device_1", "device_2", "router_1"):
            task = tasks[devId]
            task.isUp = False
            task.delayedIsUp = False

        # exercise correlator
        for x in simpleCorrelator(
            tasks, connected_ips=True, reactorYield=noOpYield
        ):
            pass

        # should have 4 down events
        eventCount = len(self._events)
        self.assertEqual(
            eventCount,
            4,
            "4 devices should be down, but got %d events" % eventCount,
        )

        # make sure we get the events we expect
        expectedEvents = {}
        expectedEvents["device_0"] = {
            "rootcause.componentId": "eth0",
            "rootcause.message": (
                "IP 'router_1_ip' on interface 'eth0' is connected to "
                "device 'router_1' and is also in the traceroute for "
                "monitored ip 'device_0_ip' on device 'device_0'"
            ),
            "rootcause.componentIP": "router_1_ip",
            "rootcause.deviceId": "router_1",
            "suppressed": True,
            "id": "device_0",
            "up": False,
        }
        expectedEvents["router_1"] = {"id": "router_1", "up": False}
        expectedEvents["device_1"] = {
            "rootcause.componentId": "eth1",
            "rootcause.message": (
                "IP 'router_1_ip_1' on interface 'eth1' is connected to "
                "device 'router_1' and is also in the traceroute for "
                "monitored ip 'device_1_ip' on device 'device_1'"
            ),
            "rootcause.deviceId": "router_1",
            "up": False,
            "rootcause.componentIP": "router_1_ip_1",
            "suppressedWithconnectedIp": "True",
            "suppressed": True,
            "id": "device_1",
        }
        expectedEvents["device_2"] = {
            "rootcause.componentId": "eth2",
            "rootcause.message": (
                "IP 'router_1_ip_2' on interface 'eth2' is connected to "
                "device 'router_1' and is also in the traceroute for "
                "monitored ip 'device_2_ip' on device 'device_2'"
            ),
            "rootcause.deviceId": "router_1",
            "up": False,
            "rootcause.componentIP": "router_1_ip_2",
            "suppressedWithconnectedIp": "True",
            "suppressed": True,
            "id": "device_2",
        }

        while len(self._events):
            actualEvent = self._events.pop()
            expectedEvent = expectedEvents.get(actualEvent["id"], None)
            self.assertIsNotNone(
                expectedEvent, "Unexpected event generated: %r" % actualEvent
            )
            self.assertDictEqual(actualEvent, expectedEvent)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestSimpleCorrelator))
    return suite
