##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from itertools import islice, ifilter
from zope.component import subscribers
from zope.interface import implements
from zope.component import getGlobalSiteManager
from Products.Zuul.facades import ZuulFacade
from interfaces import ISearchFacade, ISearchProvider,\
    ISearchQueryParser, IParsedQuery, ISavedSearchProvider

from Products.Zuul.search import ISearchResultSorter


class ParsedQuery(object):
    """
    A canonical representation of the query contents
    to be passed to an ISearchProvider.  Currently, this is only operators
    and keywords.
    """
    implements(IParsedQuery)

    def __init__(self, _operators={}, _keywords=[]):
        self.operators = _operators
        self.keywords = _keywords


def _phrasify(string):
    """
    Tokenize a string by whitespace, respecting double-quotes
    @rtype: list

    >>> _phrasify( 'a b c' )
    ['a', 'b', 'c']
    >>> _phrasify( '"a b" c' )
    ['a b', 'c']
    >>> _phrasify( '     a b' )
    ['a', 'b']
    >>> _phrasify( '"a     b" c' )
    ['a     b', 'c']
    """
    string = string.replace('"', "'")
    phrases = []
    for i, segment in enumerate(string.split("'")):
        if i % 2:
            phrases.append(segment)
        else:
            phrases.extend(segment.split(' '))
    return [ p for p in phrases if p != '' ]


class DefaultQueryParser(object):
    """
    The default implementation of ISearchQueryParser that converts a plain
    text string into a set of operators and keywords, i.e., a ParsedQuery.
    """
    implements(ISearchQueryParser)

    def parse(self, query):
        """
        For each atom in a the query string,
        categorize into keywords and operator-value pairs.
        Operators are name-value pairs separated by a colon (:).
        Keywords are anything else.

        @type query string
        @rtype IParsedQuery

        >>> parser = DefaultQueryParser()
        >>> parser.parse( 'a b c' ).keywords
        ['a', 'b', 'c']
        >>> parser.parse( 'a b c' ).operators
        {}
        >>> parser.parse( 'a:b c' ).keywords
        ['c']
        >>> parser.parse( 'a:b c' ).operators
        {'a':['b']}
        >>> parser.parse( 'a:b c:d a:e f g:' ).keywords
        ['f', 'g:']
        >>> parser.parse( 'a:b c:d a:e f g:' ).operators
        {'a':['b', 'e'], 'c':['d']}

        """
        keywords = []
        operators = {}

        for phrase in _phrasify(query):
            pair = phrase.split(':',1)
            if len(pair) == 1 or pair[0] == '':
                keywords.append(phrase)
            else:
                if pair[0] not in operators:
                    operators[pair[0]]=[]
                operators[pair[0]].append(pair[1])

        return ParsedQuery( operators, keywords )


DEVICE_CATEGORY = 'device'
EVENT_CATEGORY = 'event'

class DefaultSearchResultComparator(object):
    def __call__(self, result1, result2):
        result = self._compareCategories( result1, result2 )
        if result == 0:
            result = self._compareExcerpts( result1, result2 )
        return result

    def _compareCategories(self, result1, result2):
        cat1 = result1.category.lower()
        cat2 = result2.category.lower()

        if cat1 == cat2:
            return 0
        elif cat1 == DEVICE_CATEGORY or cat1 == EVENT_CATEGORY:
            return 1 if cat2 == DEVICE_CATEGORY else -1
        elif cat2 == DEVICE_CATEGORY or cat2 == EVENT_CATEGORY:
            return 1
        else:
            return cmp( cat1, cat2 )

    def _compareExcerpts(self, result1, result2 ):
        return cmp( result1.excerpt, result2.excerpt )

DEFAULT_SEARCH_RESULT_COMPARATOR=DefaultSearchResultComparator()

class DefaultSearchResultSorter(object):
    implements(ISearchResultSorter)

    comparator = None
    maxResults = None
    maxResultsPerCategory = None

    def __init__(self, maxResults=None,
                       maxResultsPerCategory=None,
                       resultComparator=DEFAULT_SEARCH_RESULT_COMPARATOR):
        self.comparator = resultComparator
        self.maxResults = maxResults
        self.maxResultsPerCategory = maxResultsPerCategory

    def limitSort(self, results):
        """
        Takes a list of results and returns and iterable
        of results that is sorted a limited by maxResults
        and maxPerCategory
        """
        if self.comparator is not None:
            results.sort(self.comparator)

        useCategoryLimits = self.maxResultsPerCategory is not None
        useMaxResultsLimits = self.maxResults is not None

        # We assume the results are sorted by category.
        # Take the first maxPerCategory of each group.
        categoryCounts={}
        def stillBelowCategoryLimit( result ):
            category = result.category
            if category not in categoryCounts:
                categoryCounts[category] = 0
            categoryCounts[category] += 1
            return categoryCounts[category] <= self.maxResultsPerCategory

        if useCategoryLimits:
            limitedResults = ifilter( stillBelowCategoryLimit, results )
        else:
            limitedResults = results

        if useMaxResultsLimits:
            limitedResults = islice( limitedResults, self.maxResults )
        else:
            limitedResults = limitedResults

        return limitedResults


DEFAULT_SORTER = DefaultSearchResultSorter()


class SearchFacade(ZuulFacade):
    """
    Facade for search functionality.  The SearchFacade distributes queries to
    multiple search providers and returns them as ISearchResults.
    """
    implements(ISearchFacade)

    def __init__(self, context):
        ZuulFacade.__init__(self, context)

    def _getParser(self):
        return getGlobalSiteManager().queryUtility( ISearchQueryParser )

    def _getProviders(self):
        return subscribers([self._dmd], ISearchProvider)

    def _getSavedSearchProvider(self):
        """
        @return ISavedSearchProvider: assuming one exists
        """
        gsm = getGlobalSiteManager()
        utility = gsm.queryUtility(ISavedSearchProvider, 'savedsearchprovider')
        if not utility:
            raise ValueError("No Search Provider Found")
        return utility()()

    def _getSearchResults(self, query,
                          category=None,
                          resultSorter=None,
                          filterFn=None,
                          start=0, limit=50, sort="excerpt", dir="ASC",
                          maxResults=None,
                          ):
        """
        The actual implementation of querying each provider.  This consists
        of parsing the query, sending it to the providers, and limiting
        the results if necessary.

        @param query The raw query string
        @param maxResults The maximum number of results to be returned
        @param maxResultsPerCategory The maximum number of results to be
                                     returned of any one category
        @return ordered list of ISearchResult objects
        """
        parser = self._getParser()
        parsedQuery = parser.parse( query )
        reverse = dir=='DESC'
        results = []
        for adapter in self._getProviders():
            providerResults = adapter.getSearchResults( parsedQuery,
                                                        category=category,
                                                        filterFn=filterFn,
                                                        sorter=resultSorter,
                                                        maxResults=maxResults
                                                        )

            if providerResults:
                results.extend( providerResults )
        total = len(results)
        # paginate the results
        if resultSorter:
            results =  resultSorter.limitSort( results )
        else:
            if limit:
                results = sorted(results, key=lambda row: getattr(row, sort, None), reverse=reverse)[start:limit+start]
            else:
                results = sorted(results, key=lambda row: getattr(row, sort, None), reverse=reverse)

        return dict(total=total, results=results)

    def getCategoryCounts(self, query, filterFn=None):
        """
        Query each of the adapters and find out the count of objects
        returned
        """
        parser = self._getParser()
        parsedQuery = parser.parse(query)
        results = {}
        for adapter in self._getProviders():
            providerResults = adapter.getCategoryCounts(parsedQuery, filterFn)
            if providerResults:
                for key, value in providerResults.iteritems():
                    if value > 0:
                        results[key] = value
        # sort the results
        sortedResults = []
        for key in sorted(results):
            sortedResults.append(dict(category=key, count=results[key]))
        return sortedResults

    def updateSavedSearch(self, searchName, queryString):
        """
        Updates the specified search with the specified query
        @param string searchName: name of the search we want to update
        @param string query: value of the new query we are searching on
        """
        search = self.getSavedSearch(searchName)
        search.query = queryString

    def removeSavedSearch(self, searchName):
        """
        Removes the saved search specified by searchName
        @param string searchName: search we wish to remove
        """
        provider = self._getSavedSearchProvider()
        provider.removeSearch(searchName)

    def saveSearch(self, queryString, searchName, creator):
        """
        Saves the queryString as a saved search identified by
        searchName.
        @param string queryString: term we are searching on
        @param string searchName: how we want to identify the search later
        @param string creator: user id of the person who created this search
        """
        provider = self._getSavedSearchProvider()
        provider.addSearch(queryString, searchName, creator)

    def getSavedSearch(self, searchName):
        """
        Returns the saved search specified by searchName
        @param string searchName: identifier of the search we are looking for
        """
        provider = self._getSavedSearchProvider()
        return provider.getSearch(searchName)

    def getSearchResults(self, query, category,
                         resultSorter=DEFAULT_SORTER,
                         start=0, limit=50, filterFn=None, sort="excerpt",
                         dir="ASC", page=None):
        """
        Execute the query against registered search providers, returning
        full results.

        @param query query string
        @return list of ISearchResult-implementing objects
        """
        return self._getSearchResults( query, category, resultSorter=resultSorter,
                                       filterFn=filterFn,
                                       start=start,
                                       limit=limit,
                                       sort=sort,
                                       dir=dir
                                       )

    def getQuickSearchResults(self, query, resultSorter=DEFAULT_SORTER, maxResults=None):
        """
        Execute the query against registered search providers, returning
        abbreviated results for display in the quick search drop-down list.

        @param query query string
        @return list of ISearchResult-implementing objects
        """
        return self._getSearchResults(query, resultSorter=resultSorter,
                maxResults=maxResults)

    def getSavedSearchesByUser(self):
        """
        @return [ISavedSearchProvider]
        """
        provider = self._getSavedSearchProvider()
        return provider.getAllSavedSearches()


    def noProvidersPresent(self):
        """
        Check for existence of search providers

        @return boolean
        """
        subscribers = self._getProviders()
        return subscribers is None or len(subscribers) == 0

    def noSaveSearchProvidersPresent(self):
        """
        Checks for the existence of a save provider

        @return boolean
        """
        try:
            return not self._getSavedSearchProvider()
        except ValueError:
            return True
