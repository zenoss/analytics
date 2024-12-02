##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *
from Products.ZenModel.IpNetwork import IpNetwork

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenUtils.IpUtil import IP_DELIM

class TestIpNetwork(ZenModelBaseTest):

    def testIpNetCreation(self):
        "Create valid networks"
        net = self.dmd.Networks.createNet("1.2.3.0/24")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.0',24)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        self.dmd.Networks.zDefaultNetworkTree = [ 24, 32 ]
        net = self.dmd.Networks.createNet('2.3.5.0', 26)
        net_path = "/".join(net.getPrimaryPath())
        self.assert_(net_path == '/zport/dmd/Networks/2.3.5.0/2.3.5.0')
        self.assert_(self.dmd.Networks.getNet('2.3.5.0') == net)
        parent_net = self.dmd.Networks.getNet('2.3.5.0', 24)
        self.assert_('2.3.5.0' in parent_net.objectIds())

        self.dmd.Networks.zDefaultNetworkTree = [ 8, 16, 24, 32 ]
        net = self.dmd.Networks.createNet('10.10.10.0', 26)
        net_path = "/".join(net.getPrimaryPath())
        self.assert_(net_path == '/zport/dmd/Networks/10.0.0.0/10.10.0.0/10.10.10.0/10.10.10.0')

        self.dmd.Networks.zDefaultNetworkTree = [ ]
        net = self.dmd.Networks.createNet('20.20.20.0', 26)
        self.assert_("20.20.20.0" in self.dmd.Networks.objectIds())

    def testIpV6NetCreation(self):
        "Test IPv6 networks"
        # Test a correctly specified address
        net = self.dmd.Networks.createNet('2002:ac10:10a:1234:21e:52ff:fe74:40e', 48)
        goodNetId = IP_DELIM.join(['2002', 'ac10', '10a', '', ''])
        self.assert_(goodNetId in self.dmd.Networks.getNetworkRoot(version=6).objectIds())

        # Subnet splitting is only done on /48 and /64 bit boundaries,
        # with the maximum length of subnets being /64
        net70 = self.dmd.Networks.createNet('2002:ac10:10a:1234:21e:52ff:fe74:40e', 70)
        self.assert_(goodNetId == net.getId())

        net20 = self.dmd.Networks.createNet('2002:ac10:10a:1234:21e:52ff:fe74:40e', 20)
        self.assert_(goodNetId == net.getId())

    def testBadIpNetCreation(self):
        "Test evil network masks"
        net = self.dmd.Networks.createNet("1.2.3.4/24", None)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4/24", 70)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.5',None)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.5',-1)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.5',64)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4////24", None)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4/evil", None)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4", "more evil")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

    def testIpCreation(self):
        ipobj = self.dmd.Networks.createIp("1.2.3.4", 24)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        net = self.dmd.Networks._getOb("1.2.3.0")
        self.assert_(ipobj.network() == net)

    def testGetNet(self):
        net = self.dmd.Networks.createNet('1.2.3.4/24')
        self.assert_(self.dmd.Networks.getNet('1.2.3.4') == net)
        self.assert_(self.dmd.Networks.getNet('1.2.3.8') == net)
        self.assert_(self.dmd.Networks.getNet('1.2.4.5') == None)

    def testMisc(self):
        net = self.dmd.Networks.createNet('1.2.3.0/24')
        self.assert_(net.freeIps() == 254)
        self.dmd.Networks.createIp('1.2.3.4')
        self.assert_(net.freeIps() == 253)
        self.assert_(net.countIpAddresses(inuse=False) == 1)
        self.assert_(net.getNetworkName() == '1.2.3.0/24')
        self.assert_(not net.getIpAddress('1.2.3.4') == None)
        self.assert_(net.getIpAddress('1.2.3.5') == None)
        self.assert_(self.dmd.Networks.getIpAddress('1.2.3.4') == None)
        self.assert_(net.defaultRouterIp() == '1.2.3.1')
        ipobj = net.addIpAddress('1.2.3.5')
        self.assert_(ipobj in net.ipaddresses())
    
    def testSubNetworks(self):
        dmdNet = self.dmd.Networks
        dmdNet.createNet('1.2.3.0/24')
        net = dmdNet.getSubNetwork('1.2.3.0')
        self.assert_(net in dmdNet.getSubNetworks())
        subNet = dmdNet.addSubNetwork('1.2.4.0',24)
        self.assert_(subNet in dmdNet.getSubNetworks())

    def testAutomaticNesting(self):
        dmdNet = self.dmd.Networks
        dmdNet.zDefaultNetworkTree = ['24', '32']
        dmdNet.createNet('1.2.0.0/16')
        dmdNet.createNet('1.2.3.0/24')
        net = dmdNet.findNet('1.2.0.0')
        subnet = dmdNet.findNet('1.2.3.0')
        self.assert_(subnet in net.children())

    def testAutomaticNesting2(self):
        dmdNet = self.dmd.Networks
        dmdNet.zDefaultNetworkTree = ['8', '16', '24', '32']
        dmdNet.createNet('1.2.3.0/24')
        dmdNet.createNet('1.2.4.0/24')
        net = dmdNet.findNet('1.2.0.0')
        self.assert_(dmdNet.findNet('1.2.3.0') in net.children())
        self.assert_(dmdNet.findNet('1.2.4.0') in net.children())

    def testCreateIpWithLessSpecificMask(self):
        """
        See ticket #3646.
        
        Add network 42.67.128.0/17, then create IP address 42.67.129.14 with a
        netmask of 3.  The important thing is that the netmask of the IP
        address has a less specific mask length than the network.  The IP
        address should be created directly under the network.
        """
        dmdNet = self.dmd.Networks
        # set this explicitly to the default. it should not affect this test.
        # but it is used by createIp, so just to be safe.
        dmdNet._updateProperty('zDefaultNetworkTree', (24, 32))
        
        subnet = dmdNet.addSubNetwork("42.67.128.0", 17)
        # make sure it is in the right place
        self.assertEqual(subnet, dmdNet._getOb("42.67.128.0"))
        # make sure it has the right netmask
        self.assertEqual(17, subnet.netmask)
        ip = dmdNet.createIp("42.67.129.14", 3)
        # A new network should have been created with netmask /3
        self.assert_("32.0.0.0" in dmdNet.objectIds())
        net3 = dmdNet._getOb("32.0.0.0")
        self.assertEqual(3, net3.netmask)
        # the network with netmask 17 should be a child of /3
        self.assert_("42.67.128.0" in net3.objectIds())
        net17 = net3._getOb("42.67.128.0")
        self.assertEqual(17, net17.netmask)
        # make sure the IP address is in the right place
        msg = "42.67.129.14 should be in subnet.ipaddresses(), but it is " \
              "not. subnet.ipaddresses() = %s" % subnet.ipaddresses()
        self.assert_(ip in net3.ipaddresses(), msg)
        # make sure no new networks have been created under the subnet
        self.assertEqual([], subnet.children())

    def testAutoRebalanceBackwards(self):
        """
        When creating networks, if (say) a /24 is created before a /16,
        then we need to move the /24 network tree under the new /16 network.
        Any IP addresses that are created at one level should be moved to
        the correct location.
        """
        dmdNet = self.dmd.Networks
        # Add in the 'wrong' order
        ip = dmdNet.createIp("10.10.10.1", 27)
        subnet24 = dmdNet.createNet("10.10.10.0", 24)
        ip = dmdNet.createIp("10.10.10.2", 27)
        subnet16 = dmdNet.createNet("10.10.0.0", 16)
        ip = dmdNet.createIp("10.10.10.3", 27)
        subnet8 = dmdNet.createNet("10.0.0.0", 8)

        # getPrimaryPath() ==> ('', 'zport', 'dmd', 'Networks', '10.175.211.0')
        self.assertEqual(1, len(dmdNet.children()))
        self.assertEqual(subnet8.id, dmdNet.children()[0].id)
        self.assertEqual(1, len(subnet8.children()))
        self.assertEqual(subnet16.id, subnet8.children()[0].id)
        self.assertEqual(1, len(subnet16.children()))
        self.assertEqual(subnet24.id, subnet16.children()[0].id)

    def testAutoRebalanceRandom(self):
        """
        What if the networks are created in random order?
        """
        dmdNet = self.dmd.Networks
        # Add in the 'wrong' order
        subnet24 = dmdNet.createNet("10.10.10.0", 24)
        subnet8 = dmdNet.createNet("10.0.0.0", 8)
        subnet16 = dmdNet.createNet("10.10.0.0", 16)
        subnet10 = dmdNet.createNet("10.0.0.0", 10)
        subnet20 = dmdNet.createNet("10.10.10.0", 20)
        subnet6 = dmdNet.createNet("10.0.0.0", 6)

        self.assertEqual(1, len(dmdNet.children()))
        self.assertEqual(subnet6.id, dmdNet.children()[0].id)

        self.assertEqual(1, len(subnet6.children()))
        self.assertEqual(subnet8.id, subnet6.children()[0].id)

        self.assertEqual(1, len(subnet8.children()))
        self.assertEqual(subnet10.id, subnet8.children()[0].id)

        self.assertEqual(1, len(subnet10.children()))
        self.assertEqual(subnet16.id, subnet10.children()[0].id)

        self.assertEqual(1, len(subnet16.children()))
        self.assertEqual(subnet20.id, subnet16.children()[0].id)

    def testZPropertyExistence(self):
        """
        """
        zProps = ("zDefaultNetworkTree",
                  "zDrawMapLinks",
                  "zAutoDiscover",
                  "zPingFailThresh",
                  "zIcon",
                  "zPreferSnmpNaming",
                  "zSnmpStrictDiscovery")

        def assertZPropertiesExist( network ):
            for zprop in zProps:
                self.assert_(hasattr(network,zprop))

        dmdNet = self.dmd.Networks
        assertZPropertiesExist(dmdNet)
        subnet24 = dmdNet.createNet("10.10.10.0", 24)
        assertZPropertiesExist(subnet24)

    def testFindStaleNetOrIp(self):
        """
        If we have a record in cache which is not in database it 
        should be removed from cache and return None when attempt to get it 
        """
        dmdNet = self.dmd.Networks
        # Populate cache without adding object to database
        dmdNet.get_network_cache().add_net(IpNetwork('1.1.1.0', '24'))
        net = dmdNet.findNet('1.1.1.0', '24')
        self.assertIsNone(net)
    
        dmdNet.get_network_cache().add_net(IpNetwork('2.2.2.0', '24'))
        ip = dmdNet.findIp('2.2.2.2', '24')
        self.assertIsNone(net)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpNetwork))
    return suite

if __name__=="__main__":
    framework()
