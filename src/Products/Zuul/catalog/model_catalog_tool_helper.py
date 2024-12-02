##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp, MatchGlob


class ModelCatalogToolGenericHelper(object):

    def __init__(self, model_catalog_tool, objectImplements=None, fields=None):
        """
        Helper that will automatically add query for objectImplements and
        will request the fields passed in the constructor
        """
        self.model_catalog = model_catalog_tool
        self.objectImplements = objectImplements
        if isinstance(self.objectImplements, basestring):
            self.objectImplements = [ self.objectImplements ]
        self.fields = fields
        if isinstance(self.fields, basestring):
            self.fields = [ fields ]

    def __call__(self, *args, **kwargs):
        return self.search(*args, **kwargs)

    def getBrain(self, path):
        return self.model_catalog.getBrain(path, fields=self.fields)

    def search(self, *args, **kwargs):
        if self.objectImplements:
            dict_query =  { "objectImplements" : self.objectImplements }
            current_query = kwargs.get("query")
            if not current_query:
                kwargs["query"] = dict_query
            else:
                if isinstance(current_query, dict):
                    values = current_query.get("objectImplements", [])
                    if isinstance(values, basestring):
                        values = [ values ]
                    for value in self.objectImplements:
                        if value not in values:
                            values.append(value)
                    kwargs["query"]["objectImplements"] = values
                else:
                    # it is advanced query
                    advanced_query = [ Eq("objectImplements", value) for value in self.objectImplements ]
                    if len(advanced_query) > 1:
                        advanced_query = And(*advanced_query)
                    else:
                        advanced_query = advanced_query[0]
                    kwargs["query"] = And(current_query, advanced_query)

        if self.fields:
            current_fields = kwargs.get("fields")
            if not current_fields:
                kwargs["fields"] = self.fields
            else:
                if isinstance(current_fields, basestring):
                    current_fields = [ current_fields ]
                current_fields.extend(self.fields)
                kwargs["fields"] = current_fields

        return self.model_catalog(*args, **kwargs)




class ModelCatalogToolHelper(ModelCatalogToolGenericHelper):
    """
    Helper class with methods that perform common searches in the model catalog
    """
    def __init__(self, model_catalog_tool):
        super(ModelCatalogToolHelper, self).__init__(model_catalog_tool)

    def get_device_classes(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.DeviceClass.DeviceClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_event_classes(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenEvents.EventClassInst.EventClassInst")
        return self.model_catalog.search(*args, **kwargs)

    def get_groups(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.DeviceGroup.DeviceGroup")
        return self.model_catalog.search(*args, **kwargs)

    def get_locations(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Location.Location")
        return self.model_catalog.search(*args, **kwargs)

    def get_manufacturers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Manufacturer.Manufacturer")
        return self.model_catalog.search(*args, **kwargs)

    def get_systems(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.System.System")
        return self.model_catalog.search(*args, **kwargs)

    def get_manufacturers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Manufacturer.Manufacturer")
        return self.model_catalog.search(*args, **kwargs)

    def get_mib_organizers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.MibOrganizer.MibOrganizer")
        return self.model_catalog.search(*args, **kwargs)

    def get_mibs(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.MibModule.MibModule")
        return self.model_catalog.search(*args, **kwargs)

    def get_rrd_templates(self, *args, **kwargs):
        query = Eq("objectImplements", "Products.ZenModel.RRDTemplate.RRDTemplate")
        kwargs["query"] = And(query, MatchGlob('uid', "/zport/dmd/Devices*"))
        return self.model_catalog.search(*args, **kwargs)

    def get_process_organizers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.OSProcessOrganizer.OSProcessOrganizer")
        return self.model_catalog.search(*args, **kwargs)

    def get_processes(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.OSProcessClass.OSProcessClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_report_organizers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.ReportClass.ReportClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_reports(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Report.Report")
        return self.model_catalog.search(*args, **kwargs)

    def get_services(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.ServiceClass.ServiceClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_devices(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Device.Device")
        return self.model_catalog.search(*args, **kwargs)

    def _get_device_components(self, device, str_types, *args, **kwargs):
        types = set(["Products.ZenModel.DeviceComponent.DeviceComponent"])
        if str_types:
            types = types | set(str_types)
        query = [ Eq("objectImplements", str_type) for str_type in types ]
        query.append(Eq("deviceId", "/".join(device.getPrimaryPath())))
        kwargs["query"] = And(*query)
        return self.model_catalog.search(*args, **kwargs)

    def get_device_components(self, device, *args, **kwargs):
        return self._get_device_components(device, None, *args, **kwargs)

    def get_device_interfaces(self, device, *args, **kwargs):
        str_types = [ "Products.ZenModel.IpInterface.IpInterface" ]
        return self._get_device_components(device, str_types, *args, **kwargs)

    def search_mac(self, mac_address):
        queries = []
        queries.append(Eq("objectImplements", "Products.ZenModel.IpInterface.IpInterface"))
        queries.append(Eq("macaddress", mac_address))
        return self.model_catalog.search(query=And(*queries))

