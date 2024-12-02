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
from Products.ZenUtils.Ext import DirectResponse


class ModelQueryRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to retrieve model data from Solr
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.api = Zuul.getFacade('modelquery')
        super(ModelQueryRouter, self).__init__(context, request)


    def _getFacade(self):
        return self.api


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

        devices, totalCount = self.api.getDevices(start=start, limit=limit, orderby=orderby, reverse=reverse,
                                                  params=params, fields=fields)
        return DirectResponse(devices=devices, totalCount=totalCount)


    def getIndexes(self):

        """
        Return list of dicts where each dict represents
        list of indexes for a particular object
        """

        indexes = self.api.getIndexInfo()
        return DirectResponse(indexes=indexes)

