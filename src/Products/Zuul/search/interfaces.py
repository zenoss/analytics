##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Attribute, Interface
from Products.Zuul.interfaces import IFacade, IMarshallable, IInfo


class IParsedQuery(Interface):
    """
    An set of operators and keywords resulting from the parsing of
    an input query
    """
    operators = Attribute("A hashtable of operator names to lists of values")
    keywords = Attribute("A list of keywords")


class ISearchQueryParser(Interface):
    """
    Interface for query parser implementation.  Will be returned from an
    adapter lookup so that the default parser can be replaced if needed.
    """

    def parse(query):
        """
        Take a query and return an IParsedQuery object
        """


class ISearchProvider(Interface):
    """
    Implement this interface to provide search results.
    """

    def getSearchResults(parsedQuery, sorter):
        """
        Returns a list of ISearchResult objects based on the given
        IParsedQuery.
        """

    def getQuickSearchResults(parsedQuery, sorter=None, countOnly=False,
                         category=None, unrestricted=False, filterFn=None):
        """
        Returns a list of ISearchResult objects based on the given
        IParsedQuery.  These ISearchResults may be only partially filled
        out.
        """

    def getCategoryCounts(parsedQuery, filterFn):
        """
        Returns the count of objects that satisfy the query.
        """

class ISearchResult(IMarshallable):
    """
    Implement this interface to allow objects to appear in search results.
    """

    url = Attribute("Most direct URL to the represented object")
    category = Attribute("Search category of the represented object")
    excerpt = Attribute("Small descriptive snippet for the represented object.")
    icon = Attribute("URL to the 16x16 icon for the represented object")
    popout = Attribute("True/false whether to open link in new window")


class ISearchFacade(IFacade):
    """
    Interface for a search facade.
    """
    def getQuickSearchResults(self, queryString, searchResultSorter):
        """
        Query for items, return ISearchInfo objects

        @param searchResultSorter an optional ISearchResultSorter-implementing
               object
        """

    def getSearchResults(self, queryString, searchResultSorter):
        """
        Query for items, returning ISearchInfo objects

        @param searchResultSorter an optional ISearchResultSorter-implementing
               object
        """

    def noProvidersPresent(self):
        """
        Return true if there are no providers
        """

    def saveSearch(queryString, searchName, creator):
        """
        Saves the queryString and makes it identifable by the searchName
        """

    def updateSavedSearch(searchName, queryString):
        """
        Updates the specified search with the specified query
        """

    def removeSavedSearch(searchName):
        """
        Removes the saved search specified by searchName
        """

    def getSavedSearchesByUser():
        """
        Gets all the saved searches for the currently logged in user
        """


class ISearchResultSorter(Interface):
    """
    Sort ISearchResult objects.  (The default sort is by category then excerpt.)
    """
    comparator = Attribute("Comparator for sorting search results")
    maxResults = Attribute("Maximum results to be returned from a query")
    maxResultsPerCategory = Attribute("Maximum results of any one category to" +
                                      " be returned from a query")

    def limitSort(results):
        """
        Limits and sorts search results
        """


class IQuickSearchResultSnippet(IMarshallable):
    """
    Represents the snippet of html that will be placed in the right side of
    the quick search drop down for a search result.
    """
    category = Attribute("Search category of the represented object")
    content = Attribute("The content of the search result drop down")
    url = Attribute("Link to the represented object")
    popout = Attribute("True/false whether to open link in new window")


class IQuickResultSnippetFactory(Interface):
    """
    return an IQuickSearchResultSnippet to be included in displayed results
    """


class ISavedSearchProviderFactory(Interface):
    """
    returns a saved search provider
    """


class ISavedSearchInfo(IInfo):
    """
    Represents a search that has been saved
    """
    query = Attribute("The Search term")
    creator = Attribute("User id of the person who created this saved search")


class ISavedSearchProvider(Interface):
    """
    Interface for permanently saving search queries
    """

    def addSearch(queryString, searchName, creator):
        """
        Accepts a saved Search object and add it to a permanent store
        """

    def removeSearch(searchName):
        """
        This method removes a search from our store if it exists
        """

    def getSavedSearch(searchName):
        """
        Retrieves a saved search from our repository
        @return [ISavedSearchInfo]
        """

    def getAllSavedSearches():
        """
        Retrieves all the saved search for the logged in user
        @return [ISavedSearchInfo]
        """
