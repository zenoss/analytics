##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import re
from itertools import islice

from interfaces import IModelCatalog, IModelCatalogTool
from model_catalog_tool_helper import ModelCatalogToolHelper, ModelCatalogToolGenericHelper
from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp, MatchGlob

from Products.ZenUtils.NaturalSort import natural_compare
from Products.Zuul.catalog.interfaces import IModelCatalog
from Products.Zuul.catalog.model_catalog import SearchResults, MODEL_INDEX_UID_FIELD, OBJECT_UID_FIELD
from zenoss.modelindex.constants import DEFAULT_SEARCH_LIMIT
from Products.Zuul.infos import InfoBase
from Products.Zuul.interfaces import IInfo
from Products.Zuul.tree import StaleResultsException
from Products.Zuul.utils import dottedname, allowedRolesAndGroups, unbrain
from zenoss.modelindex.model_index import SearchParams, CursorSearchParams
from zope.interface import implements
from zope.component import getUtility


log = logging.getLogger("model_catalog_tool")


class ModelCatalogTool(object):
    """ Search the model catalog """

    implements(IModelCatalogTool)

    def __init__(self, context):
        self.context = context
        self.model_catalog_client = getUtility(IModelCatalog).get_client(context)
        self.helper = ModelCatalogToolHelper(self)
        # Helpers for legacy catalogs
        self.layer2 = None
        self.layer3 = None
        self.devices = None
        self.ips = None
        self.global_catalog = None
        self._create_legacy_catalog_helpers()

    def _create_legacy_catalog_helpers(self):
        # Layer 2
        objectImplements = [ "Products.ZenModel.IpInterface.IpInterface" ]
        fields = [ "deviceId", "interfaceId", "macaddress", "lanId" ]
        self.layer2 = ModelCatalogToolGenericHelper(self, objectImplements, fields)
        # Layer 3
        fields = [ "deviceId", "interfaceId", "ipAddressId", "networkId" ]
        objectImplements = [ "Products.ZenModel.IpAddress.IpAddress" ]
        self.layer3 = ModelCatalogToolGenericHelper(self, objectImplements, fields)
        # Device catalog
        fields = [ "id", "name" ]
        objectImplements = [ "Products.ZenModel.Device.Device" ]
        self.devices = ModelCatalogToolGenericHelper(self, objectImplements, fields)
        # IpSearch (there is one per Network Tree)
        fields = [ "id", "decimal_ipAddress" ]
        objectImplements = [ "Products.ZenModel.IpAddress.IpAddress" ]
        self.ips = ModelCatalogToolGenericHelper(self, objectImplements, fields)
        # global catalog
        fields = [ "zProperties", "monitored", "name", "collectors",
                   "searchIcon", "searchExcerpt", "meta_type", "id", "uuid" ]
        self.global_catalog = ModelCatalogToolGenericHelper(self, fields=fields)

    @property
    def model_index(self):
        return self.model_catalog_client.model_index

    def _parse_user_query(self, query):
        """
        # if query is a dict, we convert it to AdvancedQuery
        # @TODO We should make the default query something other than AdvancedQuery
        """
        def _parse_basic_query(attr, value):
            if isinstance(value, str) and '*' in value:
                return MatchGlob(attr, value)
            else:
                return Eq(attr, value)

        if isinstance(query, dict):
            subqueries = []
            for attr, value in query.iteritems():
                if isinstance(value, (list, set, tuple)):
                    # If value is a list or similar, we build an OR
                    or_queries = []
                    for or_query in value:
                        or_queries.append( _parse_basic_query(attr, or_query) )
                    subqueries.append( Or(*or_queries) )
                else:
                    subqueries.append(_parse_basic_query(attr, value))
            query = And(*subqueries)
        return query

    def _build_query(self, types=(), paths=(), depth=None, query=None, filterPermissions=True, globFilters=None):
        """
        Build and AdvancedQuery query

        @params types: list/tuple of values for objectImplements field
        @params globFilters: dict with user passed field: value filters
        @params query: AdvancedQuery passed by the user. Most of the time None
        @param filterPermissions: Boolean indicating whether to check for user perms or not

        @return: tuple (AdvancedQuery query, not indexed filters dict)
        """
        indexed, stored, _ = self.model_catalog_client.get_indexes()
        not_indexed_user_filters = {} # Filters that use not indexed fields

        user_filters_query = None
        types_query = None
        paths_query = None
        permissions_query = None

        partial_queries = []
        if query:
            """
            # if query is a dict, we convert it to AdvancedQuery
            # @TODO We should make the default query something other than AdvancedQuery
            subqueries = []
            if isinstance(query, dict):
                for attr, value in query.iteritems():
                    if isinstance(value, str) and '*' in value:
                        subqueries.append(MatchGlob(attr, value))
                    else:
                        subqueries.append(Eq(attr, value))
                query = And(*subqueries)
            partial_queries.append(query)
            """
            partial_queries.append(self._parse_user_query(query))

        # Build query from filters passed by user
        if globFilters:
            for key, value in globFilters.iteritems():
                if key in indexed:
                    if user_filters_query:
                        user_filters_query = And(user_filters_query, MatchRegexp(key, value))
                    else:
                        user_filters_query = MatchRegexp(key, value)
                else:
                    not_indexed_user_filters[key] = value

        if user_filters_query:
            partial_queries.append(user_filters_query)

        # Build the objectImplements query
        if not isinstance(types, (tuple, list)):
            types = (types,)
        types_query_list = [ Eq('objectImplements', dottedname(t)) for t in types ]
        if types_query_list:
            if len(types_query_list) > 1:
                types_query = Or(*types_query_list)
            else:
                types_query = types_query_list[0]

            partial_queries.append(types_query)

        # Build query for paths
        if paths is not False:   # When paths is False we dont add any path condition
            # TODO: Account for depth or get rid of it
            # TODO: Consider indexing the device's uid as a path
            context_path = '/'.join(self.context.getPrimaryPath())
            uid_path_query = In('path', (context_path,)) # MatchGlob(UID, context_path)   # Add the context uid as filter
            partial_queries.append( uid_path_query )
            if paths:
                if isinstance(paths, basestring):
                    paths = (paths,)
                partial_queries.append( In('path', paths) )

            """  OLD CODE. Why this instead of In?  What do we need depth for?
            q = {'query':paths}
            if depth is not None:
                q['depth'] = depth
            paths_query = Generic('path', q)
            """

        # filter based on permissions
        if filterPermissions and allowedRolesAndGroups(self.context):
            permissions_query = In('allowedRolesAndUsers', allowedRolesAndGroups(self.context))
            partial_queries.append(permissions_query)

        # Put together all queries
        search_query = And(*partial_queries)
        return (search_query, not_indexed_user_filters)

    def search_model_catalog(self, query, start=0, limit=None, order_by=None, reverse=False,
                             fields=None, commit_dirty=False, facets_for_field=None):
        """
        @returns: SearchResults
        """
        catalog_results = []
        brains = []
        count = 0
        search_params = SearchParams(query, start=start, limit=limit, order_by=order_by, reverse=reverse, fields=fields)
        if facets_for_field:
            search_params.facet_field=facets_for_field
        catalog_results = self.model_catalog_client.search(search_params, self.context, commit_dirty=commit_dirty)
        return catalog_results

    def _filterQueryResults(self, queryResults, infoFilters):
        """
        filters the results by the passed in infoFilters dictionary. If the
        property of the info object is another info object the "name" attribute is used.
        The filters are applied as case-insensitive strings on the attribute of the info object.
        @param queryResults list of brains
        @param infoFilters dict: key/value pairs of filters
        @return list of brains
        """
        if not infoFilters:
            return list(queryResults)

        #Optimizing!
        results = { brain: [True, IInfo(brain.getObject())] for brain in queryResults }
        for key, value in infoFilters.iteritems():
            valRe = re.compile(".*" + unicode(value) + ".*", re.IGNORECASE)
            for result in results:
                match, info = results[result]
                if not match:
                    continue

                testvalues = getattr(info, key)
                if not hasattr(testvalues, "__iter__"):
                    testvalues = [testvalues]

                # if the property was a dictionary see if the "key" is valid
                # or if it is a dict representation of an info object, then check for the
                # name attribute.
                if isinstance(testvalues, dict):
                    val = testvalues.get(key, testvalues.get('name'))
                    if not (val and valRe.match(str(val))):
                        results[result][0] = False
                else:
                    # if anyone of these values is satisfied then include the object
                    isMatch = False
                    for testVal in testvalues:
                        if isinstance(testVal, InfoBase):
                            testVal = testVal.name
                        if valRe.match(str(testVal)):
                            isMatch = True
                            break
                    if not isMatch:
                        results[result][0] = False
        return [key for key,matches in results.iteritems() if matches[0]]

    def _sortQueryResults(self, queryResults, orderby, reverse):

        # save the values during sorting in case getting the value is slow
        savedValues = {}

        def getValue(obj):
            key = obj.getPrimaryPath()
            if key in savedValues:
                value = savedValues[key]
            else:
                value = getattr(IInfo(obj), orderby)
                if callable(value):
                    value = value()
                # if an info object is returned then sort by the name
                if IInfo.providedBy(value):
                    value = value.name.lower()
                savedValues[key] = value
            return value

        return sorted((unbrain(brain) for brain in queryResults),
                      key=getValue, reverse=reverse, cmp=natural_compare)

    def cursor_search(self, types=(), limit=DEFAULT_SEARCH_LIMIT, filterPermissions=False, fields=None):
        """
        Get all results from catalog by using solr deep pagination.
        return generator.
        """
        query, _ = self._build_query(filterPermissions=filterPermissions, types=types)
        search_params = CursorSearchParams(query, limit=limit, fields=fields)
        return self.model_catalog_client.cursor_search(search_params, self.context)

    def search(self, types=(), start=0, limit=None, orderby='name',
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None, filterPermissions=True, globFilters=None,
               fields=None, commit_dirty=False, facets_for_field=None):
        """
        Build and execute a query against the global catalog.
        @param query: Advanced Query query
        @param globFilters: dict {field: value}
        @param fields: Fields we want model index to return. The fewer 
                       fields we need to retrieve the faster the query will be
        @param facets_for_field: Field for which we want to retrieve its facets
        """
        indexed, stored, _ = self.model_catalog_client.get_indexes()
        # if orderby is not an index then query results will be unbrained and sorted
        areBrains = orderby in indexed or orderby is None
        queryOrderby = orderby if areBrains else None
        
        query, not_indexed_user_filters = self._build_query(types, paths, depth, query, filterPermissions, globFilters)

        areBrains = areBrains and len(not_indexed_user_filters) == 0
        queryStart = start if areBrains else 0
        queryLimit = limit if areBrains else None

        catalog_results = self.search_model_catalog(query, start=queryStart, limit=queryLimit,
                                                    order_by=queryOrderby, reverse=reverse,
                                                    fields=fields, commit_dirty=commit_dirty, facets_for_field=facets_for_field)
        if len(not_indexed_user_filters) > 0:
            # unbrain everything and filter
            results = self._filterQueryResults(catalog_results, not_indexed_user_filters)
            totalCount = len(results)
        else:
            results = catalog_results.results
            totalCount = catalog_results.total

        hash_ = totalCount

        if hashcheck is not None:
            if hash_ != int(hashcheck):
                raise StaleResultsException("Search results do not match")

        if not areBrains: # Even if orderby was an indexed field,, _filterQueryResults will randomize the order
            sorted_results = self._sortQueryResults(results, orderby, reverse)
            # Return a slice
            start = max(start, 0)
            if limit is None:
                stop = None
            else:
                stop = start + limit
            results = islice(sorted_results, start, stop)
        search_results = SearchResults(results, totalCount, str(hash_), areBrains)
        if catalog_results.facets:
            search_results.facets = catalog_results.facets
        return search_results

    def __call__(self, *args, **kwargs):
        return self.search(*args, **kwargs)

    def getBrainFromObject(self, ob, fields=None):
        """
        Builds a object's brain without searching model_catalog
        """
        return self.model_catalog_client.get_brain_from_object(ob, self.context, fields=fields)

    def getBrain(self, path, fields=None, commit_dirty=False):
        """
        Gets the brain representing the object defined at C{path}.
        The search is done by the object's uid field
        """
        if not isinstance(path, (tuple, basestring)):
            path = '/'.join(path.getPhysicalPath())
        elif isinstance(path, tuple):
            path = '/'.join(path)

        search_results = self.model_catalog_client.search_brain(path, context=self.context, fields=fields, commit_dirty=commit_dirty)
        brain = None
        if search_results.total > 0:
            brain = search_results.results.next()
        else:
            log.error("Unable to get brain. Trying to reindex: %s", path)
            # @TODO reindex the object if we did not find it        
        return brain

    def parents(self, path):
        """
        Get brains representing parents of C{path} + C{path}. Good for making
        breadcrumbs without waking up all the actual parent objects.
        """
        pass

    def count(self, types=(), path=None, filterPermissions=True, commit_dirty=False):
        """
        Get the count of children matching C{types} under C{path}.

        This is cheap; the lazy list returned from a catalog search knows its
        own length without exhausting its contents.

        @param types: Classes or interfaces that should be matched
        @type types: tuple
        @param path: The path under which children should be counted. Defaults
        to the path of C{self.context}.
        @type path: str
        @return: The number of children matching.
        @rtype: int
        """
        if path is None:
            path = '/'.join(self.context.getPhysicalPath())
        if not path.endswith('*'):
            path = path + '*'
        query, _ = self._build_query(types=types, paths=(path,), filterPermissions=filterPermissions)
        search_results = self.search_model_catalog(query, start=0, limit=0, commit_dirty=commit_dirty)
        """ #  @TODO OLD CODEEE had some caching stuff
        # Check for a cache
        caches = self.catalog._v_caches
        types = (types,) if isinstance(types, basestring) else types
        types = tuple(sorted(map(dottedname, types)))
        for key in caches:
            if path.startswith(key):
                cache = caches[key].get(types, None)
                if cache is not None and not cache.expired:
                    return cache.count(path)
        else:
            # No cache; make one
            results = self._queryCatalog(types, orderby=None, paths=(path,), filterPermissions=filterPermissions)
            # cache the results for 5 seconds
            cache = CountCache(results, path, time.time() + 5)
            caches[path] = caches.get(path, OOBTree())
            caches[path][types] = cache
            return len(results)
        """
        return search_results.total

    def update(self, obj):
        self.model_catalog_client.catalog_object(obj)

    def indexes(self):
        return self.model_catalog_client.get_indexes()

