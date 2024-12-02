##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re
from itertools import imap
from zope.interface import implements
from zope.component import adapts
from Products.AdvancedQuery import In, Eq
from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenUtils.IpUtil import ipToDecimal
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import SearchResults, OBJECT_UID_FIELD as UID
from Products.Zuul.interfaces import IIpNetworkInfo, IIpAddressInfo, IIpNetworkNode
from Products.Zuul.infos import InfoBase, BulkLoadMixin
from Products.Zuul.infos.catalog_tree_builder import ModelCatalogTreeBuilder
from Products.Zuul.decorators import info
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.tree import TreeNode


class IpNetworkNode(TreeNode):
    implements(IIpNetworkNode)
    adapts(IpNetwork)

    @property
    def text(self):
        numInstances = self._get_cache.get_leaf_count(self.uid)
        text = super(IpNetworkNode, self).text + '/' + str(self._object.getObject().netmask)
        return {
            'text': text,
            'count': numInstances,
            'description': 'ips'
        }

    @property
    def _get_cache(self):
        cache = getattr(self._root, '_cache', None)
        if cache is None:
            node_type = "Products.ZenModel.IpNetwork.IpNetwork"
            leaf_type = "Products.ZenModel.IpAddress.IpAddress"
            facet_field = "networkId"
            cache = ModelCatalogTreeBuilder(self._root._get_object(), node_type,
                                            leaf_type, facet_field=facet_field)
            setattr(self._root, '_cache', cache)
        return cache

    @property
    def children(self):
        nets = self._get_cache.get_children(self.uid)
        return imap(lambda x:IpNetworkNode(x, self._root, self), nets)

    @property
    def leaf(self):
        nets = self._get_cache.get_children(self.uid)
        return not nets

    @property
    def iconCls(self):
        return  ''


class IpNetworkInfo(InfoBase):
    implements(IIpNetworkInfo)

    @property
    def name(self):
        return self._object.getNetworkName()

    @property
    def ipcount(self):
        return str(self._object.countIpAddresses()) + '/' + \
               str(self._object.freeIps())

    # zProperties
    def getZAutoDiscover(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zAutoDiscover', True, translate)

    def setZAutoDiscover(self, data):
        setZPropertyInfo(self._object, 'zAutoDiscover', **data)

    zAutoDiscover = property(getZAutoDiscover, setZAutoDiscover)

    def getZDrawMapLinks(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zDrawMapLinks', True, translate)

    def setZDrawMapLinks(self, data):
        setZPropertyInfo(self._object, 'zDrawMapLinks', **data)

    zDrawMapLinks = property(getZDrawMapLinks, setZDrawMapLinks)

    def getZDefaultNetworkTree(self):
        def translate(rawValue):
            return ', '.join(str(x) for x in rawValue)
        return getZPropertyInfo(self._object, 'zDefaultNetworkTree',
                                translate=translate, translateLocal=True)

    _decimalDigits = re.compile('\d+')

    def setZDefaultNetworkTree(self, data):

        # convert data['localValue'] (string with comma and whitespace
        # delimeters) to tuple of integers
        digits = self._decimalDigits.findall( data['localValue'] )
        data['localValue'] = tuple( int(x) for x in digits )

        setZPropertyInfo(self._object, 'zDefaultNetworkTree', **data)

    zDefaultNetworkTree = property(getZDefaultNetworkTree, setZDefaultNetworkTree)

    def getZPingFailThresh(self):
        return getZPropertyInfo(self._object, 'zPingFailThresh')

    def setZPingFailThresh(self, data):
        setZPropertyInfo(self._object, 'zPingFailThresh', **data)

    zPingFailThresh = property(getZPingFailThresh, setZPingFailThresh)

    def getZIcon(self):
        return getZPropertyInfo(self._object, 'zIcon')

    def setZIcon(self, data):
        setZPropertyInfo(self._object, 'zIcon', **data)

    zIcon = property(getZIcon, setZIcon)

    def getZSnmpStrictDiscovery(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zSnmpStrictDiscovery', True, translate)

    def setZSnmpStrictDiscovery(self, data):
        setZPropertyInfo(self._object, 'zSnmpStrictDiscovery', **data)

    zSnmpStrictDiscovery = property(getZSnmpStrictDiscovery, setZSnmpStrictDiscovery)

    def getZPreferSnmpNaming(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zPreferSnmpNaming', True, translate)

    def setZPreferSnmpNaming(self, data):
        setZPropertyInfo(self._object, 'zPreferSnmpNaming', **data)

    zPreferSnmpNaming = property(getZPreferSnmpNaming, setZPreferSnmpNaming)

class IpAddressInfo(InfoBase, BulkLoadMixin):
    implements(IIpAddressInfo)

    @property
    @info
    def manageDevice(self):
        return self._object.manageDevice()

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    def netmask(self):
        return str(self._object._netmask)

    @property
    @info
    def interface(self):
        return self._object.interface()

    @property
    def macAddress(self):
        return self._object.getInterfaceMacAddress()

    @property
    def interfaceDescription(self):
        return self._object.getInterfaceDescription()

    @property
    def pingstatus(self):
        cachedValue = self.getBulkLoadProperty('pingstatus')
        if cachedValue is not None:
            return cachedValue
        if not self._object.interface():
            return 5
        return self._object.getPingStatus()

    @property
    def snmpstatus(self):
        cachedValue = self.getBulkLoadProperty('snmpstatus')
        if cachedValue is not None:
            return cachedValue
        if not self._object.interface():
            return 5
        return self._object.getSnmpStatus()
