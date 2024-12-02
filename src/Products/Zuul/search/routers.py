##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import re

from zope.interface import implements
from zope.component import adapts
from AccessControl import getSecurityManager
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products import Zuul
from Products.Zuul.search import ISearchResult
from Products.Zuul.search import IQuickSearchResultSnippet
from Products.Zuul.search import DefaultSearchResultSorter
from Products.Zuul.utils import ZuulMessageFactory as _t
from zope.component import getAllUtilitiesRegisteredFor
from Products.Zuul.search.interfaces import IQuickResultSnippetFactory


class DefaultQuickSearchResultSnippet(object):
    """
    Default representation of quick search results.  Converts icon and excerpt
    values from search results into html content for the drop-down combo
    box.
    """
    implements(IQuickSearchResultSnippet)
    adapts(ISearchResult)

    def __init__(self, result):
        self._result = result

    @property
    def category(self):
        return self._result.category

    defaultTemplate = '<table>' + \
                          '<td class="icon">%s</td>' + \
                          '<td class="excerpt">%s</td>' + \
                      '</table>'
    @property
    def content(self):
        return self.defaultTemplate % ( self._result.icon, self._result.excerpt)

    @property
    def url(self):
        return self._result.url

    @property
    def popout(self):
        return self._result.popout


_MAX_RESULTS_PER_QUERY=100
_MAX_RESULTS_PER_CATEGORY=10

_RESULT_SORTER = DefaultSearchResultSorter( _MAX_RESULTS_PER_QUERY,
                                            _MAX_RESULTS_PER_CATEGORY )

class SearchRouter(DirectRouter):
    """
    UI specific code for the search functionality.
    """

    def _getFacade(self):
        return Zuul.getFacade('search', self.context)

    def _addAllResultsLink(self, snippets, query):
        extraResults = getAllUtilitiesRegisteredFor(IQuickResultSnippetFactory)
        for factory in extraResults:
            snippets.insert(0, factory()(query))

    def _getLoggedinUserId(self):
        """
        @return String logged in users user id
        """
        securityManager = getSecurityManager()
        return securityManager.getUser()._login

    def _sanitizeQuery(self, query):
        lst = query.split(' ')
        s = set([x.strip('*') for x in lst])
        no_emtpy = [x for x in s if x]
        out_lst = [re.sub('[*]{2,}', '*', x) for x in no_emtpy]
        return ' '.join(out_lst)

    def getLiveResults(self, query, maxResults=100):
        """
        Returns IQuickSearchResultSnippets for the results of the query.
        """
        query = self._sanitizeQuery(query)
        facade = self._getFacade()
        results = facade.getQuickSearchResults(query,
                                               _RESULT_SORTER, maxResults=maxResults)
        snippets = []

        for result in results['results']:
            snippet = IQuickSearchResultSnippet( result )
            snippets.append( snippet )
        if snippets:
            self._addAllResultsLink( snippets, query )

        return {'results': Zuul.marshal(snippets)}

    def getCategoryCounts(self, query):
        """
        Given a search term this queries each of the adapters for a
        list of categories and the counts of the returned results
        """
        facade = self._getFacade()
        results = facade.getCategoryCounts(query)
        total = sum(result['count'] for result in results)
        return {'results': results,
                'total': total}

    def getAllResults(self, query, category="", start=0, limit=50, sort='excerpt', page=None,
                      dir='ASC'):
        """
        Returns ISearchResultSnippets for the results of the query.
        """
        facade = self._getFacade()
        results = facade.getSearchResults(query, category, resultSorter=None,
                                          start=start,
                                          limit=limit,
                                          sort=sort,
                                          dir=dir)
        return {'results': Zuul.marshal(results['results']),
                'total': results['total']}

    def noProvidersPresent(self):
        return self._getFacade().noProvidersPresent()

    def getSavedSearch(self, searchName):
        """
        @params string searchName: identifier of the search we are looking for
        @return DirectResponse: the data attribute will have our search terms
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.fail(message=_t('Unable to find the specified search'))

        # look for our search
        savedSearch = facade.getSavedSearch(searchName)
        if savedSearch:
            return DirectResponse.succeed(data=Zuul.marshal(savedSearch))

        # we could not find the search term
        return DirectResponse.fail(message=_t('Unable to find the specified search'))

    def updateSavedSearch(self, searchName, queryString):
        """
        Updates the specified search with the new query
        @param string searchName: name of the search we want to update
        @param string query: value of the new query we are searching on
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.succeed()

        # save the search
        facade.updateSavedSearch(searchName, queryString)
        return DirectResponse.succeed()

    def removeSavedSearch(self, searchName):
        """
        Removes the search specified by searchName
        @param string searchName
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.succeed()

        # save the search
        facade.removeSavedSearch(searchName)
        return DirectResponse.succeed()

    def saveSearch(self, queryString, searchName):
        """
        Adds this search to our collection of saved searches
        @param string queryString: term we are searching for
        @param string searchName: our query string's identifier
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.succeed()

        creator = self._getLoggedinUserId()

        # save the search
        facade.saveSearch(queryString, searchName, creator)
        return DirectResponse.succeed()

    def getAllSavedSearches(self, query=None, addManageSavedSearch=False):
        """
        @returns [ISavedSearchInfo] All the searches the logged in
        user can access
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.succeed()

        data = Zuul.marshal(facade.getSavedSearchesByUser())
        if addManageSavedSearch:
            manageName = '<span id="manage-search-link">%s</span>' % (_t('Manage Saved Searches...'))
            data.append(dict(id='manage_saved_search', name=manageName))
        return DirectResponse.succeed(data=data)
