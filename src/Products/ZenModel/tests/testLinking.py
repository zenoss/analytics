##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import json
from itertools import count, islice

from mock import patch

#import operator
#af = lambda x:x>1 and reduce(operator.add, xrange(1, x+1)) or x
#numpairs = lambda x: ((x*(x-1))*0.5) - (af(x%10)) - (af(10)*((x/10)-1))

numpairs = lambda x: (x*(x-1))*0.5

from Products.ZenModel.IpInterface import manage_addIpInterface
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from ZenModelBaseTest import ZenModelBaseTest

class TestLayer2Linking(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestLayer2Linking, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance("testdev")
        manage_addIpInterface(self.dev.os.interfaces, 'eth0', True)
        self.iface = self.dev.os.interfaces._getOb('eth0')
        self.mac = '00:11:22:33:44:55'
        self.iface._setPropValue('macaddress', self.mac)
        self.catalog = IModelCatalogTool(self.dmd).layer2

    def testIndexAttributes(self):
        brain = list(self.catalog())[0]
        self.assertEqual(brain.deviceId, '/zport/dmd/Devices/devices/' + self.dev.id)
        self.assertEqual(brain.interfaceId, self.iface.getPrimaryId())
        self.assertEqual(brain.macaddress, self.mac)
        self.assertEqual(brain.lanId, None)

    def testMacIndex(self):
        brain = list(self.catalog())[0]
        self.assertEqual(brain.macaddress, self.mac)
        MAC = '55:44:33:22:11:00'
        self.iface._setPropValue('macaddress', MAC)
        brain = list(self.catalog())[0] # need a search to trigger indexing
        self.assertEqual(brain.macaddress, MAC)


class TestLayer3Linking(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestLayer3Linking, self).afterSetUp()
        self.globalInt = count()
        self.devices = {}
        self.evids = []
        self.zem = self.dmd.ZenEventManager

    def assertSameObs(self, *stuff):
        idsort = lambda a,b:cmp(a.id, b.id)
        for l in stuff:
            l.sort(idsort)
        return self.assertEqual(*stuff)

    def _getSubnet(self, base=None, netmask=24):
        if not base: base = self.globalInt.next()
        return ('10.0.%d.%d' % (base, ip) for ip in count())

    def _makeDevices(self, num):
        devgen = ((i, self.dmd.Devices.createInstance("dev%d" % i)) 
                  for i in self.globalInt)
        self.devices.update(dict((i, dev) for (i, dev) in islice(devgen, num)))
        return self.devices

    def _linkDevices(self, devs):
        subnet = self._getSubnet()
        for i in devs:
            dev = devs[i]
            iid = self.globalInt.next()
            manage_addIpInterface(dev.os.interfaces, 'eth%d'%iid, True)
            iface = dev.os.interfaces._getOb('eth%d'%iid)
            iface.addIpAddress(subnet.next())

    @patch("Products.ZenModel.LinkManager.getFacade")
    def testzDrawMapLinksProperty(self, getFacade):
        devs = self._makeDevices(6)

        devs[0].setLocation('/A')
        devs[1].setLocation('/A')
        devs[2].setLocation('/B')
        devs[3].setLocation('/C')
        devs[4].setLocation('/D')
        devs[5].setLocation('/A')

        manage_addIpInterface(devs[0].os.interfaces, 'eth0', True)
        iface0 = devs[0].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[1].os.interfaces, 'eth0', True)
        iface1 = devs[1].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[2].os.interfaces, 'eth0', True)
        iface2 = devs[2].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[3].os.interfaces, 'eth0', True)
        iface3 = devs[3].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[4].os.interfaces, 'eth0', True)
        iface4 = devs[4].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[5].os.interfaces, 'eth0', True)
        iface5 = devs[5].os.interfaces._getOb('eth0')

        iface0.addIpAddress('192.168.254.9/30')
        iface2.addIpAddress('192.168.254.10/30')

        iface1.addIpAddress('192.168.254.5/30')
        iface3.addIpAddress('192.168.254.6/30')

        iface4.addIpAddress('192.168.254.1/30')
        iface5.addIpAddress('192.168.254.2/30')

        nononet = self.dmd.Networks.getNet('192.168.254.8')
        nononet.zDrawMapLinks = False

        links = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        links = json.loads(links)
        self.assertEqual(len(links), 2)

    @patch("Products.ZenModel.LinkManager.getFacade")
    def testSlash30Nets(self, getFacade):
        devs = self._makeDevices(6)

        devs[0].setLocation('/A')
        devs[1].setLocation('/A')
        devs[2].setLocation('/B')
        devs[3].setLocation('/C')
        devs[4].setLocation('/D')
        devs[5].setLocation('/A')

        manage_addIpInterface(devs[0].os.interfaces, 'eth0', True)
        iface0 = devs[0].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[1].os.interfaces, 'eth0', True)
        iface1 = devs[1].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[2].os.interfaces, 'eth0', True)
        iface2 = devs[2].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[3].os.interfaces, 'eth0', True)
        iface3 = devs[3].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[4].os.interfaces, 'eth0', True)
        iface4 = devs[4].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[5].os.interfaces, 'eth0', True)
        iface5 = devs[5].os.interfaces._getOb('eth0')

        iface0.addIpAddress('192.168.254.9/30')
        iface2.addIpAddress('192.168.254.10/30')

        iface1.addIpAddress('192.168.254.5/30')
        iface3.addIpAddress('192.168.254.6/30')

        iface4.addIpAddress('192.168.254.1/30')
        iface5.addIpAddress('192.168.254.2/30')

        links = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        links = json.loads(links)
        self.assertEqual(len(links), 3)


    def testGetLinkedNodes(self):
        devs = self._makeDevices(3)
        ateam = {0:devs[0], 1:devs[1]}
        bteam = {2:devs[2], 1:devs[1]}
        self._linkDevices(ateam)
        self._linkDevices(bteam)

        def getLinkDevs(start):
            brains, been_there = self.dmd.ZenLinkManager.getLinkedNodes(
                'Device', start.id)
            device_ids = set( [ brain.deviceId for brain in brains ] )
            return [ self.dmd.unrestrictedTraverse(uid) for uid in device_ids ]
        self.assertSameObs(getLinkDevs(devs[0]), ateam.values())
        self.assertSameObs(getLinkDevs(devs[1]), [devs[0], devs[1], devs[2]])
        self.assertSameObs(getLinkDevs(devs[2]), bteam.values())

    @patch("Products.ZenModel.LinkManager.getFacade")
    def testGetChildLinks(self, getFacade):
        numDevices = 36
        devs = self._makeDevices(numDevices)
        self._linkDevices(devs)
        devs = devs.values()
        while devs:
            these, devs = devs[:6], devs[6:]
            for this in these:
                this.setLocation("/loc_%d" % len(devs))
        locs = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        locs = json.loads(locs)
        self.assertEqual(len(locs), 15) # (n!)/(k!(n-k)!), n=6, k=2

    @patch("Products.ZenModel.LinkManager.getFacade")
    def testLinkStatus(self, getFacade):
        devs = self._makeDevices(3)

        devs[0].setLocation('/A')
        devs[1].setLocation('/A')
        devs[2].setLocation('/B')

        self.dmd.Locations.A.address = 'A'
        self.dmd.Locations.B.address = 'B'

        self._linkDevices({1:devs[1], 2:devs[2]})

        # evt = dict(device=devs[0].id, summary="Test Event", 
        #            eventClass='/Status/Ping', severity=5)

        # self.evids.append(self.zem.sendEvent(evt))

        links = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        links = json.loads(links)

        self.assertEqual(len(links), 1)
        # Can't test event severity anymore because events are async
        # self.assertEqual(links[0][1], 0)

        # evt = dict(device=devs[1].id, summary="Test Event", 
        #            eventClass='/Status/Ping', severity=5)

        # self.evids.append(self.zem.sendEvent(evt))

        links = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        links = json.loads(links)

        self.assertEqual(len(links), 1)
        # Can't test event severity anymore because events are async
        # self.assertEqual(links[0][1], 5)

    def beforeTearDown(self):
        if self.evids:
            conn = self.zem.connect()
            try:
                curs = conn.cursor()
                for evid in self.evids:
                    curs.execute("delete from status where evid='%s'" % evid)
            finally: 
                self.zem.close(conn)
        super(TestLayer3Linking, self).beforeTearDown()


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestLayer3Linking))
    suite.addTest(makeSuite(TestLayer2Linking))
    return suite
