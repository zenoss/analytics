##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import math

from ipaddr import IPNetwork

from Products.Zuul.catalog.interfaces import IIndexableWrapper
from Products.ZenUtils.IpUtil import ipunwrap, isip

from zenoss.modelindex import indexed, index
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD
from zenoss.modelindex.field_types import StringFieldType, ListOfStringsFieldType, IntFieldType, UntokenizedStringFieldType, ListOfUntokenizedStringsFieldType, ListOfPathStringsFieldType
from zenoss.modelindex.field_types import DictAsBase64StringsFieldType, LongFieldType, NotIndexedFieldType, BooleanFieldType, DoubleFieldType
from zenoss.modelindex.field_types import IPAddressFieldType
from zenoss.modelindex.constants import NOINDEX_TYPE


MODEL_INDEX_UID_FIELD = INDEX_UNIQUE_FIELD  # this will translate to "modelindex_uid" in solr
OBJECT_UID_FIELD = "uid"                    # this will transalate to "uid" in solr

"""
    @TODO:
        Review how and where we index IpAddresses and macs since currently we are indexing
        them in several places (Device, IpInterface, IpAddress)


    Set of abstract classes designed to add indexable attributes to zenoss objects.
    Most methods start with idx_ to avoid conflicts with pre existing attributes/methods

        BaseIndexable:

            ----------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |  TYPE     | TOKENIZED |
            ----------------------------------------------------------------------------------------------------------------------
            |  idx_model_index_uid       |  modelindex_uid         | modelindex_uid  |     Y   |    Y    |   str     |     N     |
            |  idx_object_uid            |  uid                    |       uid       |     Y   |    Y    |   str     |     N     |
            |  idx_id                    |  id                     |                 |     Y   |    Y    |   str     |     N     |
            |  idx_uuid                  |  uuid                   |                 |     Y   |    Y    |   str     |     N     |
            |  idx_name                  |  name                   |                 |     Y   |    Y    |   str     |     N     |
            |  idx_meta_type             |  meta_type              |                 |     Y   |    Y    |   str     |     N     |
            |  idx_path                  |  path                   |                 |     Y   |    Y    | list(str) |     Y     |
            |  idx_objectImplements      |  objectImplements       |                 |     Y   |    Y    | list(str) |     Y     |
            |  idx_allowedRolesAndUsers  |  allowedRolesAndUsers   |                 |     Y   |    Y    | list(str) |     Y     |
            |  idx_searchKeywords        |  searchKeywords         |                 |     Y   |    Y    | list(str) |     N     |
            |  idx_searchExcerpt         |  searchExcerpt          |                 |     N   |    Y    |   str     |     N     |
            |  idx_searchIcon            |  searchIcon             |                 |     N   |    Y    |   str     |     N     |
            |  idx_monitored             |  monitored              |                 |     Y   |    Y    |   bool    |           |
            |  idx_collectors            |  collectors             |                 |     Y   |    Y    | list(str) |     Y     |
            |  idx_productionState       |  productionState        |                 |     Y   |    Y    |   int     |           |
            |  idx_zProperties           |  zProperties            |                 |     N   |    Y    | dict(str) |           |
            |  idx_decimal_ipAddress     |  decimal_ipAddress      |                 |     Y   |    Y    |   str     |     Y     |
            |  idx_macAddresses          |  macAddresses           |                 |     Y   |    Y    | list(str) |     Y     |
            ----------------------------------------------------------------------------------------------------------------------

        DeviceIndexable:

            -------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME  | INDEXED |  STORED |  TYPE     | TOKENIZED |
            -------------------------------------------------------------------------------------------------------------------
            |  idx_text_ipAddress        |  text_ipAddress         |              |     Y   |    Y    |   str     |     Y     |
            |  idx_deviceClassPath       |  deviceClassPath        |              |     Y   |    N    |   str     |     N     |
            |  idx_deviceOrganizers      |  deviceOrganizers       |              |     Y   |    Y    |   str     |     N     |
            |  idx_tagNumber             |  tagNumber              |              |     Y   |    Y    |   str     |     N     |
            |  idx_pythonClass           |  pythonClass            |              |     Y   |    Y    |   str     |     N     |     
            |  idx_priority              |  priority               |              |     Y   |    Y    |   str     |     N     |
            |  idx_collector             |  collector              |              |     Y   |    Y    |   str     |     N     |
            |  idx_osModel               |  osModel                |              |     Y   |    Y    |   str     |     N     |
            |  idx_osManufacturer        |  osManufacturer         |              |     Y   |    Y    |   str     |     N     |
            |  idx_hwModel               |  hwModel                |              |     Y   |    Y    |   str     |     N     |
            |  idx_hwManufacturer        |  hwManufacturer         |              |     Y   |    Y    |   str     |     N     |
            |  idx_serialNumber          |  serialNumber           |              |     Y   |    Y    |   str     |     N     |
            |  idx_snmpLastCollection    |  snmpLastCollection     |              |     Y   |    Y    |   double  |     N     |
            -------------------------------------------------------------------------------------------------------------------


        ComponentIndexable:

            -------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME  | INDEXED |  STORED |  TYPE     | TOKENIZED |
            -------------------------------------------------------------------------------------------------------------------
            |  idx_deviceId              |  deviceId               |              |     Y   |    Y    |   str     |     Y     |
            |  idx_description           |  description            |              |     Y   |    Y    |   str     |     Y     |
            -------------------------------------------------------------------------------------------------------------------


        IpInterfaceIndexable:

            -----------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                      |  ATTR_QUERY_NAME    |  FIELD NAME     | INDEXED |  STORED |  TYPE     | TOKENIZED |
            -----------------------------------------------------------------------------------------------------------------------
            |  idx_interfaceId                |   interfaceId       |                 |     Y   |    Y    |   str     |     Y     |
            |  idx_text_ipAddress             |   text_ipAddress    |                 |     Y   |    Y    |   str     |     Y     |
            |  idx_lanId                      |   lanId             |                 |     Y   |    Y    |   str     |     Y     |
            |  idx_macaddress                 |   macaddress        |                 |     Y   |    Y    |   str     |     Y     |
            -----------------------------------------------------------------------------------------------------------------------

        IpAddressIndexable:

            ---------------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                         |  ATTR_QUERY_NAME     |  FIELD NAME     | INDEXED |  STORED |  TYPE     | TOKENIZED |
            ---------------------------------------------------------------------------------------------------------------------------
            |   idx_interfaceId                  |   interfaceId        |                 |     Y   |    Y    |   str     |     Y     |
            |   idx_ipAddressId                  |   ipAddressId        |                 |     Y   |    Y    |   str     |     Y     |
            |   idx_networkId                    |   networkId          |                 |     Y   |    Y    |   str     |     N     |
            |   idx_deviceId                     |   deviceId           |                 |     Y   |    Y    |   str     |     Y     |
            |   idx_decimal_ipAddress            |   NOINDEX_TYPE       | DISABLE SUPERCLASS SPEC FIELD                               |
            |   idx_ipaddress_decimal_ipAddress  |   decimal_ipAddress  |                 |     Y   |    Y    |   str     |     Y     |
            |   idx_ipAddressAsText              |   ipAddressAsText    |                 |     Y   |    Y    |   str     |     Y     |
            ---------------------------------------------------------------------------------------------------------------------------

        IpNetworkIndexable:

            ----------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |  TYPE     | TOKENIZED |
            ----------------------------------------------------------------------------------------------------------------------
            |   idx_firstDecimalIp       |   firstDecimalIp        |                 |     Y   |    Y    |   str     |     Y     |
            |   idx_lastDecimalIp        |   lastDecimalIp         |                 |     Y   |    Y    |   str     |     Y     |
            ----------------------------------------------------------------------------------------------------------------------

        ProductIndexable:

            ----------------------------------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |  TYPE     | TOKENIZED |
            ----------------------------------------------------------------------------------------------------------------------
            |   idx_productClassId       |   productClassId        |                 |     Y   |    Y    |   str     |     N     |
            ----------------------------------------------------------------------------------------------------------------------

        ###########

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            ----------------------------------------------------------------------------------------------
"""

""" Indexed Fields formatters """

def decimal_ipAddress_formatter(value):
    if value is not None:
        if not isinstance(value, basestring):
            value = str(value)
        return value.zfill(39)
    else:
        return value

""" Indexable classes """

class TransactionIndexable(object):
    """
    Internal fields to temporaty index documents that have been committed
    to model index mid transaction
    """

    @indexed(LongFieldType(stored=True), attr_query_name="tx_state")
    def idx_tx_state(self):
        """
        Transaction state. We use this field to be able to tell
        if the document was updated by a committed transaction or by an
        ongoing transaction. By default we assume we all documents were
        indexed by commited transactions. The transaction manager will fill
        this appropriately before sending it to solr
        """
        return 0


class BaseIndexable(TransactionIndexable):    # ZenModelRM inherits from this class
    '''
    @indexed(StringFieldType(stored=True), attr_query_name="indexable"):
    def idx_base_indexable(self):
        return self.__class__.__name__
    '''

    def idx_uid(self):
        return IIndexableWrapper(self).uid()

    # modelindex requires that every object has an 'index_field_name' and  'attr_query_name'
    # named MODELINDEX_UID. This field is used as unique field in the index.
    # We use the object's primary path. The model catalog data manager adds additional information
    # to this field for mid transaction commits. This way we can have several documents for the same object
    @indexed(UntokenizedStringFieldType(stored=True), index_field_name=MODEL_INDEX_UID_FIELD, attr_query_name=MODEL_INDEX_UID_FIELD)
    def idx_model_index_uid(self):
        return self.idx_uid()

    # uid used within zenoss. it is the object's primary path
    @indexed(UntokenizedStringFieldType(stored=True), index_field_name=OBJECT_UID_FIELD, attr_query_name=OBJECT_UID_FIELD)
    def idx_object_uid(self):
        return self.idx_uid()

    @indexed(UntokenizedStringFieldType(stored=True), attr_query_name="id")
    def idx_id(self):
        return self.id

    @indexed(UntokenizedStringFieldType(stored=True), attr_query_name="uuid")
    def idx_uuid(self):
        """
        Object's uuid.
        """
        return IIndexableWrapper(self).uuid()

    @indexed(UntokenizedStringFieldType(stored=True), attr_query_name="name")
    def idx_name(self):
        """
        The name of the object.
        """
        return IIndexableWrapper(self).name()

    @indexed(UntokenizedStringFieldType(stored=True), attr_query_name="meta_type")
    def idx_meta_type(self):
        """
        Object's meta_type. Mostly used for backwards compatibility.
        """
        return IIndexableWrapper(self).meta_type()

    @indexed(ListOfPathStringsFieldType(stored=True), attr_query_name="path") # Device already has a method called path
    def idx_path(self):
        """
        Paths under which this object may be found.
        """
        return [ '/'.join(p) for p in IIndexableWrapper(self).path() ]

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="objectImplements")
    def idx_objectImplements(self):
        """
        All interfaces and classes implemented by an object.
        """
        return IIndexableWrapper(self).objectImplements()

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="allowedRolesAndUsers")
    def idx_allowedRolesAndUsers(self):
        """
        Roles and users with View permission.
        """
        return IIndexableWrapper(self).allowedRolesAndUsers()


    # Fields for Searchables
    @indexed(ListOfUntokenizedStringsFieldType(stored=True), attr_query_name="searchKeywords")
    def idx_searchKeywords(self):
        keywords = IIndexableWrapper(self).searchKeywords()
        if keywords:
            unique_keywords = { keyword for keyword in keywords if keyword }
            return list(unique_keywords)
        else:
            return []

    @indexed(UntokenizedStringFieldType(indexed=False, stored=True), attr_query_name="searchExcerpt")
    def idx_searchExcerpt(self):
        return IIndexableWrapper(self).searchExcerpt()

    @indexed(UntokenizedStringFieldType(indexed=False, stored=True), attr_query_name="searchIcon")
    def idx_searchIcon(self):
        return IIndexableWrapper(self).searchIcon()


    # Fields for components
    @indexed(bool, attr_query_name="monitored")
    def idx_monitored(self):
        return True if IIndexableWrapper(self).monitored() else False

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="collectors")
    def idx_collectors(self):
        cols = IIndexableWrapper(self).collectors()
        if cols:
            return [ col for col in cols if col ]
        else:
            return []

    # Fields for devices
    @indexed(IntFieldType(stored=True), attr_query_name="productionState")
    def idx_productionState(self):
        return IIndexableWrapper(self).productionState()

    @indexed(DictAsBase64StringsFieldType(indexed=False), attr_query_name="zProperties")
    def idx_zProperties(self):
        return IIndexableWrapper(self).zProperties

    # Fields for Devices and Interfaces
    @indexed(StringFieldType(stored=True, index_formatter=decimal_ipAddress_formatter, query_formatter=decimal_ipAddress_formatter), attr_query_name="decimal_ipAddress") # Ip address as number
    def idx_decimal_ipAddress(self):

        return IIndexableWrapper(self).ipAddress

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="macAddresses")
    def idx_macAddresses(self):
        return IIndexableWrapper(self).macAddresses()

class DeviceIndexable(object):   # Device inherits from this class

    def _idx_get_ip(self):
        if hasattr(self, 'getManageIp') and self.getManageIp():
            return self.getManageIp().partition('/')[0]
        else:
            return None

    @indexed(IPAddressFieldType(stored=True, index_formatter=ipunwrap, query_formatter=ipunwrap), attr_query_name="text_ipAddress")
    def idx_text_ipAddress(self):
        return self._idx_get_ip()

    @indexed(UntokenizedStringFieldType(indexed=True, stored=False), attr_query_name="deviceClassPath")
    def idx_deviceClassPath(self):
        return self.getDeviceClassPath()

    @indexed(ListOfUntokenizedStringsFieldType(indexed=True, stored=True), attr_query_name="deviceOrganizers")
    def idx_deviceOrganizers(self):
        """
        device organizers the device belongs to as untokenized strings so we can use facets
        to get the device organizer counts in the infrastructure page
        """
        paths = self.idx_path()
        relevant_organizers = { "Devices", "Groups", "Locations", "Systems" }
        organizers = []
        for path in paths:
            sp = path.split("/")
            if len(sp) >= 6 and sp[3] in relevant_organizers and sp[-2] == "devices":
                # remove the devices/device_id from the end
                organizers.append( "/".join(sp[:-2]) )
        return organizers

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="tagNumber")
    def idx_tagNumber(self):
        return self.hw.tag
 
    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="pythonClass")
    def idx_pythonClass(self):
        return self.__class__.__module__

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="priority")
    def idx_priority(self):
        return self.priority

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="collector")
    def idx_collector(self):
        return self.getPerformanceServerName()

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="osModel")
    def idx_osModel(self):
        if self.os.productClass():
            return self.os.productClass().id

        return None

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="osManufacturer")
    def idx_osManufacturer(self):
        if self.os.productClass():
            return self.os.productClass().manufacturer().id

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="hwModel")
    def idx_hwModel(self):
        if self.hw.productClass():
            return self.hw.productClass().id

        return None

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="hwManufacturer")
    def idx_hwManufacturer(self):
        if self.hw.productClass():
            return self.hw.productClass().manufacturer().id

    @indexed(StringFieldType(indexed=True, stored=True), attr_query_name="serialNumber")
    def idx_serialNumber(self):
        return self.hw.serialNumber

    @indexed(DoubleFieldType(indexed=True, stored=True), attr_query_name="snmpLastCollection")
    def idx_snmpLastCollection(self):
        return self.snmpLastCollection


class ComponentIndexable(object):     # DeviceComponent inherits from this class

    @indexed(StringFieldType(stored=True), attr_query_name="deviceId")
    def idx_deviceId(self):
        """ device the component belongs to """
        device_id = None
        if self.device():
            device_id = self.device().idx_uid()
        return device_id

    @indexed(StringFieldType(stored=True), attr_query_name="description")
    def idx_description(self):
        """ description of the component """
        description = None
        if self.description:
            description = self.description
        return description

class IpInterfaceIndexable(ComponentIndexable): # IpInterface inherits from this class

    @indexed(StringFieldType(stored=True), attr_query_name="interfaceId")
    def idx_interfaceId(self):
        interface_id = None
        if self.interfaceId():
            interface_id = self.interfaceId()
        return interface_id

    def _idx_get_ip(self):
        if hasattr(self, 'getIpAddress') and self.getIpAddress():
            return self.getIpAddress().partition('/')[0]
        else:
            return None

    @indexed(IPAddressFieldType(stored=True, index_formatter=ipunwrap, query_formatter=ipunwrap), attr_query_name="text_ipAddress")
    def idx_text_ipAddress(self):
        return self._idx_get_ip()

    """ Layer 2 catalog indexes """
    @indexed(StringFieldType(stored=True), attr_query_name="lanId")
    def idx_lanId(self):
        lan_id = None
        if self.lanId() and self.lanId()!="None":
            lan_id = self.lanId()
        return lan_id

    @indexed(StringFieldType(stored=True), attr_query_name="macaddress")
    def idx_macaddress(self):
        return self.macaddress


class IpAddressIndexable(object):  # IpAddress inherits from this class

    """ Layer 3 catalog indexes """

    @indexed(StringFieldType(stored=True), attr_query_name="interfaceId")
    def idx_interfaceId(self):
        interface_id = None
        if self.interfaceId():
            interface_id = self.interface().interfaceId()
        return interface_id

    @indexed(StringFieldType(stored=True), attr_query_name="ipAddressId")
    def idx_ipAddressId(self):
        return self.ipAddressId()

    @indexed(UntokenizedStringFieldType(stored=True), attr_query_name="networkId")
    def idx_networkId(self):
        return self.networkId()

    @indexed(StringFieldType(stored=True), attr_query_name="deviceId")
    def idx_deviceId(self):
        """ device the ipaddress belongs to. Since IpAddress does not inherit from DeviceComponent """
        device_id = None
        if self.device():
            device_id = self.device().idx_uid()
        return device_id

    """ ipSearch catalog indexes """
    index("idx_decimal_ipAddress", NOINDEX_TYPE) # disable BaseIndexable implementation
    @indexed(StringFieldType(stored=True, index_formatter=decimal_ipAddress_formatter, query_formatter=decimal_ipAddress_formatter), attr_query_name="decimal_ipAddress")
    def idx_ipaddress_decimal_ipAddress(self):
        return str(self.ipAddressAsInt())

    @indexed(IPAddressFieldType(stored=True, index_formatter=ipunwrap, query_formatter=ipunwrap), attr_query_name="ipAddressAsText")
    def idx_ipAddressAsText(self):
        return self.getIpAddress()


class IpNetworkIndexable(object):

    """ IpNetwork indexes """

    # largest 128 decimal is 340282366920938463463374607431768211456
    # we need to fill to 39 chars for range queries to work

    @indexed(StringFieldType(stored=True, index_formatter=decimal_ipAddress_formatter, query_formatter=decimal_ipAddress_formatter), attr_query_name="firstDecimalIp")
    def idx_firstDecimalIp(self):
        first_decimal_ip = None
        if isip(self.id):
            net = IPNetwork(ipunwrap(self.id))
            first_decimal_ip = str(int(net.network))
        return first_decimal_ip

    @indexed(StringFieldType(stored=True, index_formatter=decimal_ipAddress_formatter, query_formatter=decimal_ipAddress_formatter), attr_query_name="lastDecimalIp")
    def idx_lastDecimalIp(self):
        last_decimal_ip = None
        if isip(self.id):
            net = IPNetwork(ipunwrap(self.id))
            first_decimal_ip = long(int(net.network))
            last_decimal_ip = str(long(first_decimal_ip + math.pow(2, net.max_prefixlen - self.netmask) - 1))
        return last_decimal_ip

class ProductIndexable(object):
    """
    Indexable for MEProduct
    ProductClass used to have a relationship between product <-> productClass that caused
    ConflictErrors. To avoid them we index the path to the productClass for each Product
    """
    @indexed(UntokenizedStringFieldType(stored=True), attr_query_name="productClassId")
    def idx_productClassId(self):
        product_class = ""
        pc = self.productClass()
        if pc:
            product_class = pc.idx_uid()
        return product_class
