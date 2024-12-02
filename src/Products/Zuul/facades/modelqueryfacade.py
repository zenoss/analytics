##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products import Zuul
from Products.Zuul.routers import TreeRouter
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog_tool_helper import ModelCatalogToolHelper
from Products.ZenUtils.Ext import DirectResponse



class ModelQueryFacade(ZuulFacade):


    def __init__(self, context):

        self.context = context
        super(ModelQueryFacade, self).__init__(context)
        self.model_catalog = IModelCatalogTool(self.context)
        self.model_catalog_helper = ModelCatalogToolHelper(self.model_catalog)
        self.indexed, self.stored, self.fields_by_type = self.model_catalog.model_catalog_client.get_indexes()


    def filterIndexes(self, indexes):

        # Sensitive information which may be stored as a value for zProp in SOLR is not encrypted yet
        # while that exclude it from the query.
        filtered = ["zProperties"]
        return [index for index in indexes if index not in filtered]


    def getDevices(self, start=0, limit=200, orderby=None, reverse=False, params=None, fields=None):
        """
        Retrieves a list of devices.
        @type  limit: integer
        @param limit: (optional) Number of items to return

        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search
                        e.g. params={'name': 'localhost'}

        @type  fields: list of strings
        @param fields: (optional) list of indexed fields to retrieve, if None
        then attempts to retrive values for all indexes we have in SOLR.
                        e.g. fields=["name", "osModel", "productionState"]

        """

        if fields is None:
            indexes = self._getIndexes()
            indexes.append('events')
        else:
            indexes = self.filterIndexes(fields)

        if 'uuid' not in indexes:
            indexes.append('uuid')

        # in case customer uses not indexed fields to filter results in SOLR remove them from the query
        if params:
            for parameter in params.keys():
                if parameter not in self.indexed:
                    params.pop(parameter)

        results = self.model_catalog_helper.get_devices(start=start, limit=limit, orderby=orderby, reverse=reverse,
                                                        globFilters=params, fields=indexes)
        devices = [brain.to_dict(indexes) for brain in results]

        if 'events' in indexes:
            uuids = [dev['uuid'] for dev in devices]
            zep = Zuul.getFacade('zep', self.context.dmd.primaryAq())
            severities = zep.getEventSeverities(uuids)
            for device in devices:
                events = dict((zep.getSeverityName(sev).lower(), counts) for (sev, counts) in severities[device['uuid']].iteritems())
                device['events'] = events

        return devices, results.total


    def _getIndexes(self):

        idxs = self.filterIndexes(self.indexed.union(self.stored))
        return idxs


    def getIndexInfo(self):

        results = []
        for field in self.fields_by_type.items():
            if isinstance(field[0], type):
                idxs = []
                for index in field[1]:
                    idx = dict(
                        index_field_name=index.index_field_name,
                        attr_query_name=index.attr_query_name,
                        indexed=index.index_field_type.indexed,
                        stored=index.index_field_type.stored
                    )

                    idxs.append(idx)

                results.append({field[0].__name__:idxs})

        return results



