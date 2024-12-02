##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from OFS.SimpleItem import SimpleItem
from Products.AdvancedQuery import And, Or, Not, Eq
from Products.Zuul.catalog.interfaces import IModelCatalogTool


#------------------------------------------------------
#                  Value Converters
#------------------------------------------------------

default_value_converter = lambda value: value

last_part_of_path_value_converter = lambda value: value.split("/")[-1]

def strip_zport_dmd_value_converter(value):
    if value.startswith("/zport/dmd"):
        return value[10:]
    return value

def add_zport_dmd_value_converter(value):
    if not value.startswith("/zport/dmd"):
        return "{}{}".format("/zport/dmd", value)
    return value

def device_catalog_path_value_converter(value):
    """
    device catalog returns the path a a tuple and
    removes the name of the relationship
    """
    paths = []
    for path in value:
        pt = tuple(path.split("/"))
        if pt and pt[-2]=="devices":
            pt = pt[:-2] + pt[-1:]
        paths.append(pt)
    return paths

#------------------------------------------------------

class TranslationValueConverter(object):
    """ """
    def __init__(self, search=None, result=None):
        self.search_converter = default_value_converter
        self.result_converter = default_value_converter
        if search is not None:
            self.search_converter = search
        if result is not None:
            self.result_converter = result


DEFAULT_CONVERTER = TranslationValueConverter()


class LegacyFieldTranslation(object):
    def __init__(self, old, new, value_converter=None):
        self.old = old
        self.new = new
        self.value_converter = DEFAULT_CONVERTER
        if value_converter is not None:
            self.value_converter = value_converter


#------------------------------------------------------
#           Translations for legacy  catalogs
#------------------------------------------------------


GLOBAL_CATALOG_TRANSLATIONS =[
    LegacyFieldTranslation(old="uid", new="uid",
                           value_converter=TranslationValueConverter(
                                            search=add_zport_dmd_value_converter
                                            )),
    LegacyFieldTranslation(old="id", new="id"),
    LegacyFieldTranslation(old="name", new="name"),
    LegacyFieldTranslation(old="meta_type", new="meta_type"),
    LegacyFieldTranslation(old="objectImplements", new="objectImplements"),
    LegacyFieldTranslation(old="path", new="path"),
    LegacyFieldTranslation(old="searchIcon", new="searchIcon"),
    LegacyFieldTranslation(old="searchKeywords", new="searchKeywords"),
    LegacyFieldTranslation(old="searchExcerpt", new="searchExcerpt"),
    LegacyFieldTranslation(old="allowedRolesAndUsers", new="allowedRolesAndUsers"),
    LegacyFieldTranslation(old="monitored", new="monitored"),
    LegacyFieldTranslation(old="macAddresses", new="macAddresses"),
    LegacyFieldTranslation(old="ipAddress", new="text_ipAddress"),
    LegacyFieldTranslation(old="uuid", new="uuid"),
    # LegacyFieldTranslation(old="productKeys", new="productKeys"), we currently dont have it
    LegacyFieldTranslation(old="zProperties", new="zProperties"),
    LegacyFieldTranslation(old="collectors", new="collectors"),
]


DEVICE_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="getDeviceIp", new="text_ipAddress"),
    LegacyFieldTranslation(old="getPhysicalPath", new="uid"),
    LegacyFieldTranslation(old="titleOrId", new="name"),
    LegacyFieldTranslation(old="id", new="id"),
    LegacyFieldTranslation(old="getPrimaryId", new="uid"),
    LegacyFieldTranslation(old="path", new="path",
                           value_converter=TranslationValueConverter(
                                result=device_catalog_path_value_converter)),
    LegacyFieldTranslation(old="getDeviceClassPath", new="deviceClassPath"),
    LegacyFieldTranslation(old="getAdminUserIds", new="adminUserIds"),
]


LAYER_2_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="macaddress", new="macaddress"),
    LegacyFieldTranslation(old="interfaceId", new="interfaceId"),
    LegacyFieldTranslation(old="deviceId", new="deviceId"),
    LegacyFieldTranslation(old="lanId", new="lanId"),
]


LAYER_3_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="networkId", new="networkId"),
    LegacyFieldTranslation(old="interfaceId", new="interfaceId",
                           value_converter=TranslationValueConverter(
                                result=last_part_of_path_value_converter)),
    LegacyFieldTranslation(old="ipAddressId", new="ipAddressId"),
    LegacyFieldTranslation(old="deviceId", new="deviceId",
                           value_converter=TranslationValueConverter(
                                result=last_part_of_path_value_converter)),
]


IP_SEARCH_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="path", new="uid", value_converter=TranslationValueConverter()),
    LegacyFieldTranslation(old="ipAddressAsInt", new="decimal_ipAddress",
                           value_converter=TranslationValueConverter(result=str)),
    LegacyFieldTranslation(old="id", new="id"),
]


TRANSLATIONS = {
    "global_catalog" : GLOBAL_CATALOG_TRANSLATIONS,
    "deviceSearch"   : DEVICE_CATALOG_TRANSLATIONS,
    "layer2_catalog" : LAYER_2_CATALOG_TRANSLATIONS,
    "layer3_catalog" : LAYER_3_CATALOG_TRANSLATIONS,
    "ipSearch"       : IP_SEARCH_CATALOG_TRANSLATIONS,
}


#------------------------------------------------------


class LegacyFieldsTranslator(object):
    def __init__(self):
        self.old_fields = {}
        self.new_fields = {}

    def add_translations(self, translations):
        """
        @param translations iterable of LegacyFieldTranslation
        """
        for translation in translations:
            self.add_field_translation(translation)

    def add_field_translation(self, field_translation):
        self.old_fields[field_translation.old] = field_translation
        self.new_fields[field_translation.new] = field_translation

    def translate(self, old=None, new=None):
        translation = None
        if old:
            translation = old # We dont have a translation
            if self.old_fields.get(old):
                translation = self.old_fields[old].new
        if new:
            translation = new # We dont have a translation
            if self.new_fields.get(new):
                translation = self.new_fields[new].old
        return translation

    def convert_result_value(self, old, value):
        if value and old in self.old_fields:
            converter = self.old_fields[old].value_converter.result_converter
            value = converter(value)
        return value

    def convert_search_value(self, old, value):
        if value and old in self.old_fields:
            converter = self.old_fields[old].value_converter.search_converter
            if converter != default_value_converter:
                new_value = value
                if isinstance(value, basestring):
                    new_value = converter(value)
                elif isinstance(value, tuple) or (value, list):
                    new_value = [ converter(v) for v in value ]
                    if isinstance(query._term, tuple):
                        new_value = tuple(new_value)
                else:
                    pass # Not likely since only uid uses a search converter (for now....)
                return new_value
        return value

    def get_old_field_names(self):
        return self.old_fields.keys()

    def get_new_field_names(self):
        return self.new_fields.keys()


class MockZCatalog(object):
    def delIndex(self, index):
        pass


class LegacyCatalogAdapter(SimpleItem):
    """
    Adapt the ZCatalog interface to use model catalog for searching.
    For every search it:
        - parses the query to replace the legacy catalog indexes (fields names)
          with model catalog field names
        - sends the request to model catalog
        - converts the brains received from model catalog adding legacy catalog
          field, updating the value if needed
    """
    def __init__(self, context, zcatalog_name=None):
        """
        @param context: context to instanciate IModelCatalogTool
        @param zcatalog_name: string representing the legacyCatalog we are adapting
        """
        self.context = context
        self.zcatalog_name = zcatalog_name
        self._catalog = MockZCatalog()

    def _get_translator(self):
        translator = LegacyFieldsTranslator()
        if TRANSLATIONS.get(self.zcatalog_name):
            translations = TRANSLATIONS.get(self.zcatalog_name)
            translator.add_translations(translations)
        return translator

    def _get_model_catalog(self):
        model_catalog = IModelCatalogTool(self.context)
        if self.zcatalog_name == "deviceSearch":
            model_catalog = model_catalog.devices
        elif self.zcatalog_name == "layer2_catalog":
            model_catalog = model_catalog.layer2
        elif self.zcatalog_name == "layer3_catalog":
            model_catalog = model_catalog.layer3
        elif self.zcatalog_name == "ipSearch":
            model_catalog = model_catalog.ips
        return model_catalog

    def __call__(self, query=None, **kw):
        return self.search(query, **kw)

    def __len__(self):
        model_catalog = self._get_model_catalog()
        return model_catalog.search(limit=0).total


    def searchResults(self, query=None, **kw):
        return self.search(query, **kw)

    def evalAdvancedQuery(self, query, **kw):
        # evalAdvancedQuery(query, sortSpecs=(), withSortValues=_notPassed)
        # @TODO try to do something with the sorting....
        return self.search(query)

    def _adapt_advancedQuery_query(self, translator, query):
        # we need to translate the legacy catalog fields to model catalog fields
        if isinstance(query, And) or isinstance(query, Or):
            for q in query._subqueries:
                self._adapt_advancedQuery_query(translator, q)
        elif isinstance(query, Not):
            self._adapt_advancedQuery_query(translator,query._query)
        else:
            old_field_name = query._idx
            query._idx = translator.translate(old=old_field_name)
            query._term = translator.convert_search_value(old_field_name, query._term)
        return query

    def _adapt_dict_query(self, translator, query):
        new_query = {}
        for field, value in query.iteritems():
            new_field = translator.translate(old=field)
            new_value = translator.convert_search_value(field, value)
            new_query[new_field] = new_value
        return new_query

    def _adapt_query(self, translator, query):
        """
        modifies a query for a legacy catalog into a model catalog query
        @param query AdvancedQuery or dict for the legacy catalog
        """
        if isinstance(query, dict):
            return self._adapt_dict_query(translator, query)
        else:
            return self._adapt_advancedQuery_query(translator, query)

    def _adapt_brains(self, translator, search_results):
        """
        @param search_results model catalog search results
        @return 
        """
        converted_brains = []
        for brain in search_results:
            # add the legacy catalog fields to the brain
            for old_field_name in translator.get_old_field_names():
                new_field_name = translator.translate(old=old_field_name)
                value = getattr(brain, new_field_name)
                value = translator.convert_result_value(old_field_name, value)
                setattr(brain, old_field_name, value)
            converted_brains.append(brain)
        return converted_brains

    def getIndexes(self):
        return self._get_translator().get_old_field_names()

    def search(self, query, sort_index=None, reverse=False, limit=None, **kw):
        """
        Perform search on Model Catalog tweaking query and results to match legacy
        indexes and expected data format
        """
        model_catalog = self._get_model_catalog()
        translator = self._get_translator()
        search_kw = {}
        old_fields = translator.get_old_field_names()

        # Check kw args for query terms
        dict_query = {name:value for name, value in kw.items() if name in old_fields}

        # merge with any existing query
        if dict_query:
            if not query:
                query = dict_query
            elif isinstance(query, dict):
                query.update(dict_query)
            else:
                aq_from_dict = And(*[Eq(name, value) for name, value in dict_query.items()])
                query = And(query, aq_from_dict)

        if query:
            query = self._adapt_query(translator, query)
        if sort_index:
            search_kw["orderby"] = sort_index
        search_kw["reverse"] = reverse
        search_kw["limit"] = limit
        search_kw["fields"] = translator.get_new_field_names()
        search_results = model_catalog.search(query=query, **search_kw)
        legacy_brains = self._adapt_brains(translator, search_results)
        return legacy_brains


"""

#===================================================
#                 GLOBAL CATALOG
#===================================================

#--------------------------
#          INDEXES        #
#--------------------------

monitored   
name                    u'performance'
collectors  
searchKeywords  
allowedRolesAndUsers    OOSet([u'Manager', u'ZenManager', u'ZenOperator', u'ZenUser'])
meta_type               u'MonitorClass'
macAddresses    
path                    OOSet(['/zport/dmd/Monitors/Performance'])
objectImplements        OOSet([u'Products.ZenModel.MonitorClass.MonitorClass', ... ])
ipAddress   
id                      u'Performance'
productKeys 
uid                     u'Monitors/Performance'

#--------------------------
#         METADATA        #
#--------------------------

zProperties             {}
monitored               None
name                    Performance
collectors              None
searchIcon              None
searchExcerpt           None
meta_type               MonitorClass
id                      Performance
uuid                    None

#===================================================
#                 DEVICE CATALOG
#===================================================

#--------------------------
#          INDEXES        #
#--------------------------

"getDeviceIp"        : "text_ipAddress"       # u'10.171.51.2'
"getPhysicalPath"    : "uid",                 # /zport/dmd/Devices/Server/Linux/devices/10.171.51.2
"path"               : "path"                 # OOSet(['/zport/dmd/Devices/Server/Linux/10.171.51.2', '/zport/dmd/Systems/hola/10.171.51.2'])
"titleOrId"          : "name"                 # u'10.171.51.2'
"id"                 : "id"                   # u'10.171.51.2'
"getDeviceClassPath" :                 # u'/server/linux'
"getAdminUserIds"    :                 # OOSet([u'admin'])  # Added by ZenPacks.zenoss.ZenDeviceACL

#--------------------------
#         METADATA        #
#--------------------------

"getPrimaryId": "uid"                   # /zport/dmd/Devices/Server/Linux/devices/10.171.51.2
"id"          : "id"                    # 10.171.51.2
"path"        : "path"  POSTPROCESS     # [('', 'zport', 'dmd', 'Systems', 'hola', '10.171.51.2'), ('', 'zport', 'dmd', 'Devices', 'Server', 'Linux', '10.171.51.2')]

#===================================================
#                 LAYER 2 CATALOG
#===================================================

#--------------------------
#          INDEXES        #
#--------------------------

macaddress          u'00:11:93:3a:9e:c1'
interfaceId         u'/zport/dmd/devices/http/devices/10.171.51.2/os/interfaces/gigabitethernet1_10'
deviceId            u'/zport/dmd/devices/http/devices/10.171.51.2'
lanId               u'none'

#--------------------------
#         METADATA        #
#--------------------------

macaddress     00:11:93:3A:9E:C1
interfaceId    /zport/dmd/Devices/HTTP/devices/10.171.51.2/os/interfaces/GigabitEthernet1_10
deviceId       /zport/dmd/Devices/HTTP/devices/10.171.51.2
lanId          None

#===================================================
#                 LAYER 3 CATALOG
#===================================================

#--------------------------
#          INDEXES        #
#--------------------------

networkId       u'/zport/dmd/networks/10.104.85.0'
interfaceId     u'vlan800'
ipAddressId     u'/zport/dmd/networks/10.104.85.0/ipaddresses/10.104.85.248'
deviceId        u'10.171.51.2'

#--------------------------
#         METADATA        #
#--------------------------

networkId       /zport/dmd/Networks/10.104.85.0
interfaceId     Vlan800
ipAddressId     /zport/dmd/Networks/10.104.85.0/ipaddresses/10.104.85.248
deviceId        10.171.51.2


#===================================================
#       IP SEARCH CATALOG  (1 per network tree)
#===================================================

#--------------------------
#          INDEXES        #
#--------------------------

path             OOSet(['/zport/dmd/Networks/10.104.108.0/ipaddresses/10.104.108.1'])
ipAddressAsInt   u'174615553'
id               u'10.104.108.1'

#--------------------------
#         METADATA        #
#--------------------------

NADA

"""


