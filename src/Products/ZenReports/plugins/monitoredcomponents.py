##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.AdvancedQuery import Eq
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.ZenReports.AliasPlugin import AliasPlugin
from Products.ZenReports import Utils
from Products.ZenUtils.AutoGCObjectReader import gc_cache_every


class monitoredcomponents(AliasPlugin):
    """
    Fetches every component in the system. Returns a generator of
    dictionaries with metadata about each component so we can quickly
    invalidate the component.
    This keeps the memory usage in check.
    """

    def getSubComponents(self, dmd):
        catalog = IModelCatalogTool(dmd.Devices)
        COMPONENT = "Products.ZenModel.DeviceComponent.DeviceComponent"
        query = Eq("monitored", "1")
        with gc_cache_every(100, db=dmd._p_jar._db):
            for brain in catalog.search(COMPONENT, query=query):
                try:
                    obj = brain.getObject()
                except KeyError:
                    continue
                status = obj.getStatus()
                row = dict(
                    getParentDeviceTitle=obj.getParentDeviceTitle(),
                    hostname=obj.getParentDeviceTitle(),
                    name=obj.name(),
                    meta_type=obj.meta_type,
                    getInstDescription=obj.getInstDescription(),
                    getStatusString=obj.convertStatus(status),
                    getDeviceLink=obj.getDeviceLink(),
                    getPrimaryUrlPath=obj.getPrimaryUrlPath(),
                    cssclass=obj.getStatusCssClass(status),
                    status=status,
                )
                yield Utils.Record(**row)

    def run(self, dmd, args):
        # ZEN-30539
        if args.get("adapt", ""):
            return []
        return self.getSubComponents(dmd)
