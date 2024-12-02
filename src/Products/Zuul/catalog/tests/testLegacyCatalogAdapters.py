##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from Products.AdvancedQuery import Eq, Or
from Products.ZenModel.IpInterface import manage_addIpInterface
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.IpUtil import ipToDecimal
from Products.Zuul.catalog.legacy import LegacyCatalogAdapter


DEVICE_CLASS = 'my_device_class_{}'
LOCATION = 'location_{}'
DEVICE = "my_device_{}"
MAC = '00:11:22:33:44:0{}'
IP = '10.10.{}.{}/24'


class MockDevice(object):
    def __init__(self):
        self.device_class = None
        self.location = None
        self.device = None
        self.interface = None
        self.ip = None


class TestLegacyCatalogAdapters(BaseTestCase):

    def afterSetUp(self):
        super(TestLegacyCatalogAdapters, self).afterSetUp()
        self.global_catalog = LegacyCatalogAdapter(self.dmd, "global_catalog")
        self.device_catalog = LegacyCatalogAdapter(self.dmd.Devices, "deviceSearch")
        self.layer2_catalog = LegacyCatalogAdapter(self.dmd, "layer2_catalog")
        self.layer3_catalog = LegacyCatalogAdapter(self.dmd, "layer3_catalog")
        self.ip_catalog     = LegacyCatalogAdapter(self.dmd.Networks, "ipSearch")

        self.n_devices = 5
        self.devices = {}
        for dev_id in xrange(self.n_devices):
            dev = MockDevice()
            dev.device_class = self.dmd.Devices.createOrganizer(DEVICE_CLASS.format(dev_id))
            dev.location = self.dmd.Locations.createOrganizer(LOCATION.format(dev_id))
            dev.device = dev.device_class.createInstance(DEVICE.format(dev_id))
            dev.device.setLocation("/".join(dev.location.getPrimaryPath())[10:])
            iface_name = 'eth{}'.format(dev_id)
            manage_addIpInterface(dev.device.os.interfaces, iface_name, True)
            iface = dev.device.os.interfaces._getOb(iface_name)
            iface._setPropValue('macaddress', MAC.format(dev_id))
            iface.addIpAddress(IP.format(dev_id, dev_id))
            dev.ip = iface.ipaddresses()[0]
            dev.device.setManageIp(dev.ip.id)
            dev.interface = iface
            self.devices[dev_id] = dev

    def validate_global_catalog(self):
        # Get Devices using AdvancedQuery
        query = Eq("objectImplements", "Products.ZenModel.Device.Device")
        brains = self.global_catalog.search(query)
        self.assertEqual(len(brains), self.n_devices)
        # Get Devices using dict query
        query = {"objectImplements": "Products.ZenModel.Device.Device"}
        brains = self.global_catalog.search(query)
        self.assertEqual(len(brains), self.n_devices)

        # Get Locations
        query = Eq("objectImplements", "Products.ZenModel.Location.Location")
        brains = self.global_catalog.search(query)
        self.assertEqual(len(brains), self.n_devices + 1) # n_devices plus root node

        # Get Devices
        query = []
        query.append(Eq("objectImplements", "Products.ZenModel.Device.Device"))
        query.append(Eq("objectImplements", "Products.ZenModel.IpAddress.IpAddress"))
        brains = self.global_catalog.search(Or(*query))
        self.assertEqual(len(brains), 2*self.n_devices)

        # Get a device by uid
        d = self.devices[0]
        uid = "/".join(d.device.getPrimaryPath())
        # global_catalog strips /zport/dmd/
        uid = uid[10:]
        # using AdvancedQuery
        brains = self.global_catalog.search(Eq("uid", uid))
        self.assertEqual(len(brains), 1)
        # using dict query
        brains = self.global_catalog.search({"uid": uid})
        self.assertEqual(len(brains), 1)

    def validate_device_catalog(self):
        # get all devices
        brains = self.device_catalog()
        self.assertEqual(len(brains), self.n_devices)

        # Grab a device and perform diferent searches
        for dev in self.devices.values():
            uid = "/".join(dev.device.getPrimaryPath())
            titleOrId = dev.device.id
            ip = dev.ip.id
            queries = [ ("titleOrId", titleOrId),
                        ("getDeviceIp", ip),
                        ("getPhysicalPath", uid) ]
            for q_field, q_value in queries:
                brains = self.device_catalog.search(Eq(q_field, q_value))
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].getPrimaryId, uid)
                self.assertEqual(brains[0].id, dev.device.id)
                self.assertEqual(sorted(brains[0].path), sorted(dev.device.path()))

                # Search with keywords as the query
                kw = {q_field:q_value}
                brains = self.device_catalog(**kw)
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].getPrimaryId, uid)
                self.assertEqual(brains[0].id, dev.device.id)
                self.assertEqual(sorted(brains[0].path), sorted(dev.device.path()))

            # Search with name=value format
            brains = self.device_catalog(getPhysicalPath=uid)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].getPrimaryId, uid)
            self.assertEqual(brains[0].id, dev.device.id)
            self.assertEqual(sorted(brains[0].path), sorted(dev.device.path()))

            # Search with both (query is AdvancedQuery)
            query = Eq("titleOrId", titleOrId)
            brains = self.device_catalog(query=query, getDeviceIp=ip)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].getPrimaryId, uid)
            self.assertEqual(brains[0].id, dev.device.id)
            self.assertEqual(sorted(brains[0].path), sorted(dev.device.path()))

            # Search with both (query is dict)
            query = {"getDeviceIp": ip}
            brains = self.device_catalog(query=query, titleOrId=titleOrId, getPhysicalPath=uid)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].getPrimaryId, uid)
            self.assertEqual(brains[0].id, dev.device.id)
            self.assertEqual(sorted(brains[0].path), sorted(dev.device.path()))



    def validate_layer2_catalog(self):
        # get all ip interfaces
        brains = self.layer2_catalog()
        self.assertEqual(len(brains), self.n_devices)
        # perform diferent searches for each of the devices
        for dev in self.devices.values():
            device_uid = "/".join(dev.device.getPrimaryPath())
            interface_uid = "/".join(dev.interface.getPrimaryPath())
            mac = dev.interface.macaddress
            queries = [ ("macaddress", mac),
                        ("interfaceId", interface_uid),
                        ("deviceId", device_uid) ]
            for q_field, q_value in queries:
                brains = self.layer2_catalog.search(Eq(q_field, q_value))
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].deviceId, device_uid)
                self.assertEqual(brains[0].interfaceId, interface_uid)
                self.assertEqual(brains[0].macaddress, mac)

                # Search with keywords as the query
                kw = {q_field:q_value}
                brains = self.layer2_catalog(**kw)
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].deviceId, device_uid)
                self.assertEqual(brains[0].interfaceId, interface_uid)
                self.assertEqual(brains[0].macaddress, mac)

            # Search with both (query is AdvancedQuery)
            query = Eq("macaddress", mac)
            brains = self.layer2_catalog(query, interfaceId=interface_uid)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].deviceId, device_uid)
            self.assertEqual(brains[0].interfaceId, interface_uid)
            self.assertEqual(brains[0].macaddress, mac)

            # Search with both (query is dict)
            query = {"macaddress":mac}
            brains = self.layer2_catalog(query, interfaceId=interface_uid)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].deviceId, device_uid)
            self.assertEqual(brains[0].interfaceId, interface_uid)
            self.assertEqual(brains[0].macaddress, mac)

    def validate_layer3_catalog(self):
        # get all ip interfaces
        brains = self.layer3_catalog()
        self.assertEqual(len(brains), self.n_devices)
        # perform diferent searches for each of the devices
        for dev in self.devices.values():
            device_id = dev.device.id
            ip_address_uid = "/".join(dev.ip.getPrimaryPath())
            interface_id = dev.interface.id
            network_uid = "/".join(dev.ip.network().getPrimaryPath())
            queries = [ ("networkId", network_uid),
                        ("interfaceId", interface_id),
                        ("ipAddressId", ip_address_uid),
                        ("deviceId", device_id) ]
            for q_field, q_value in queries:
                brains = self.layer3_catalog.search(Eq(q_field, q_value))
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].networkId, network_uid)
                self.assertEqual(brains[0].interfaceId, interface_id)
                self.assertEqual(brains[0].ipAddressId, ip_address_uid)
                self.assertEqual(brains[0].deviceId, device_id)

                # Search with keywords as the query
                kw = {q_field:q_value}
                brains = self.layer3_catalog(**kw)
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].networkId, network_uid)
                self.assertEqual(brains[0].interfaceId, interface_id)
                self.assertEqual(brains[0].ipAddressId, ip_address_uid)
                self.assertEqual(brains[0].deviceId, device_id)

            # Search with both (query is AdvancedQuery)
            query = Eq("networkId", network_uid)
            brains = self.layer3_catalog(query, interfaceId=interface_id)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].networkId, network_uid)
            self.assertEqual(brains[0].interfaceId, interface_id)
            self.assertEqual(brains[0].ipAddressId, ip_address_uid)
            self.assertEqual(brains[0].deviceId, device_id)

            # Search with both (query is dict)
            query = {"networkId": network_uid}
            brains = self.layer3_catalog(query, interfaceId=interface_id)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].networkId, network_uid)
            self.assertEqual(brains[0].interfaceId, interface_id)
            self.assertEqual(brains[0].ipAddressId, ip_address_uid)
            self.assertEqual(brains[0].deviceId, device_id)

    def validate_ip_catalog(self):
        # get all ips
        brains = self.ip_catalog()
        self.assertEqual(len(brains), self.n_devices)
        for dev in self.devices.values():
            ip_id = dev.ip.id
            ip_as_int = ipToDecimal(ip_id)
            path = "/".join(dev.ip.getPrimaryPath())
            queries = [ ("path", path),
                        ("ipAddressAsInt", ip_as_int),
                        ("id", ip_id) ]
            for q_field, q_value in queries:
                brains = self.ip_catalog.search(Eq(q_field, q_value))
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].path, path)
                self.assertEqual(int(brains[0].ipAddressAsInt), ip_as_int)
                self.assertEqual(brains[0].id, ip_id)

                # Search with keywords as the query
                kw = {q_field:q_value}
                brains = self.ip_catalog(**kw)
                self.assertEqual(len(brains), 1)
                self.assertEqual(brains[0].path, path)
                self.assertEqual(int(brains[0].ipAddressAsInt), ip_as_int)
                self.assertEqual(brains[0].id, ip_id)

            # Search with both (query is AdvancedQuery)
            query = Eq("path", path)
            brains = self.ip_catalog(query, id=ip_id)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].path, path)
            self.assertEqual(int(brains[0].ipAddressAsInt), ip_as_int)
            self.assertEqual(brains[0].id, ip_id)

            # Search with both (query is dict)
            query = {"path": path}
            brains = self.ip_catalog(query, id=ip_id)
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].path, path)
            self.assertEqual(int(brains[0].ipAddressAsInt), ip_as_int)
            self.assertEqual(brains[0].id, ip_id)

            # Negative test
            brains = self.ip_catalog(query, id="bad_id")
            self.assertEqual(len(brains), 0)

    def test_legacy_catalogs(self):
        self.validate_global_catalog()
        self.validate_device_catalog()
        self.validate_layer2_catalog()
        self.validate_layer3_catalog()
        self.validate_ip_catalog()


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestLegacyCatalogAdapters),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
