

import logging


from interfaces import IModelCatalog, IModelCatalogTool
from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp, MatchGlob

from Products.Zuul.catalog.interfaces import IModelCatalog
from Products.Zuul.utils import dottedname, allowedRolesAndGroups
from zenoss.modelindex.model_index import SearchParams
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID
from zope.interface import implements
from zope.component import getUtility


log = logging.getLogger("model_catalog_tool")


class ModelCatalogTool(object):
    """ Search the model catalog """

    implements(IModelCatalogTool)

    def __init__(self, context):
        self.context = context
        self.model_catalog_client = getUtility(IModelCatalog).get_client(context)
        self.uid_field_name = UID

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
        available_indexes = self.model_catalog_client.get_indexes()
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
                if key in available_indexes:
                    if user_filters_query:
                        user_filters_query = And(query, MatchRegexp(key, '*%s*' % value))
                    else:
                        user_filters_query = MatchRegexp(key, '*%s*' % value)
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
            context_path = '/'.join(self.context.getPhysicalPath()) + '*'
            if not paths:
                paths = (context_path, )
            elif isinstance(paths, basestring):
                paths = (paths,)

            """  OLD CODE. Why this instead of In?  What do we need depth for?
            q = {'query':paths}
            if depth is not None:
                q['depth'] = depth
            paths_query = Generic('path', q)
            """
            paths_query = In('path', paths)
            uid_path_query = MatchGlob(UID, context_path)   # Add the context uid as filter
            partial_queries.append( Or(paths_query, uid_path_query) )

        # filter based on permissions
        if filterPermissions and allowedRolesAndGroups(self.context):
            permissions_query = In('allowedRolesAndUsers', allowedRolesAndGroups(self.context))
            partial_queries.append(permissions_query)

        # Put together all queries
        search_query = And(*partial_queries)
        return (search_query, not_indexed_user_filters)

    def search_model_catalog(self, query, start=0, limit=None, order_by=None, reverse=False, fields=None):
        """
        @returns: SearchResults
        """
        catalog_results = []
        brains = []
        count = 0
        search_params = SearchParams(query, start=start, limit=limit, order_by=order_by, reverse=reverse, fields=fields)
        catalog_results = self.model_catalog_client.search(search_params, self.context)

        return catalog_results

    def _get_fields_to_return(self, uid_only, fields):
        """
        return the list of fields that brains returned by the current search will have
        """
        if isinstance(fields, basestring):
            fields = [ fields ]
        brain_fields = set(fields) if fields else set()
        if uid_only:
            brain_fields.add(self.uid_field_name)
        return list(brain_fields)

    def search(self, types=(), start=0, limit=None, orderby='name',
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None, filterPermissions=True, globFilters=None, uid_only=True, fields=None):
        """
        Build and execute a query against the global catalog.
        @param query: Advanced Query query
        @param globFilters: dict {field: value}
        @param uid_only: if True model index will only return the uid
        @param fields: Fields we want model index to return. The fewer 
                       fields we need to retrieve the faster the query will be
        """
        available_indexes = self.model_catalog_client.get_indexes()
        # if orderby is not an index then query results will be unbrained and sorted
        areBrains = orderby in available_indexes or orderby is None
        queryOrderby = orderby if areBrains else None
        
        query, not_indexed_user_filters = self._build_query(types, paths, depth, query, filterPermissions, globFilters)

        #areBrains = len(not_indexed_user_filters) == 0

        # if we have not indexed fields, we need to get all the results and manually filter and sort
        # I guess that with solr we should be able to avoid searching by unindexed fields
        #
        # @TODO get all results if areBrains == False
        #
        
        fields_to_return = self._get_fields_to_return(uid_only, fields)

        catalog_results = self.search_model_catalog(query, start=start, limit=limit,
                                                    order_by=orderby, reverse=reverse, fields=fields_to_return)

        # @TODO take care of unindexed filters
        return catalog_results


    def getBrain(self, path, fields=None):
        """
        Gets the brain representing the object defined at C{path}.
        The search is done by uid field
        """
        if not isinstance(path, (tuple, basestring)):
            path = '/'.join(path.getPhysicalPath())
        elif isinstance(path, tuple):
            path = '/'.join(path)

        query = Eq(UID, path)
        search_results = self.search_model_catalog(query, fields=fields)

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

    def count(self, types=(), path=None, filterPermissions=True):
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
        search_results = self.search_model_catalog(query, start=0, limit=0)
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

