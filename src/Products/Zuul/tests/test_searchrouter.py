##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os.path
from zope.component import getGlobalSiteManager
from zope.component import adapts
from zope.interface import implements

from Products.ZenModel.DataRoot import DataRoot
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IFacade
from Products.Zuul.search import ISearchFacade
from Products.Zuul.search import ISearchResult
from Products.Zuul.search import IQuickSearchResultSnippet
from Products.Zuul.search import SearchRouter
from Products.Zuul.interfaces import IMarshaller
from Products.Zuul.marshalling import Marshaller


import logging
log = logging.getLogger("zen.search")

search_results = None

class DummyFacade(object):
    implements( ISearchFacade )
    adapts( DataRoot )

    def __init__(self,dmd):
        pass

    def getQuickSearchResults(self, query, resultSorter=None, maxResults=None):
        return dict(results=search_results)

    def getSearchResults(self, query):
        return search_results

class DummySearchResult(object):
    implements( ISearchResult )

    def __init__(self, url, category, excerpt, icon, popout=None):
        self.url = url
        self.category = category
        self.excerpt = excerpt
        self.icon = icon
        self.popout = popout

class DummySearchSnippet(object):
    implements( IQuickSearchResultSnippet )
    adapts( DummySearchResult )

    def __init__(self, result):
        self.url = result.url
        self.category = result.category
        self.content = result.icon + result.excerpt
        self.popout = result.popout

search_results = None

def _createDummyResult( index, popout ):
    return DummySearchResult(
        'url%s' % index,
        'cat%s' % index,
        'exc%s' % index,
        'icon%s' % index,
        popout
        )

def _createJSONInfo( index, popout ):
    return {'category': 'cat%s' % index,
            'content': 'icon%s' % index + 'exc%s' % index,
            'url': 'url%s' % index,
            'popout': popout }

class TestSearchRouter(BaseTestCase):

    def afterSetUp(self):
        super(TestSearchRouter, self).afterSetUp()

        global search_results
        search_results = None
        gsm = getGlobalSiteManager()
        gsm.registerAdapter( DummyFacade, (DataRoot,), IFacade, 'search' )
        gsm.registerAdapter( DummySearchSnippet, (ISearchResult,), IQuickSearchResultSnippet )
        gsm.registerAdapter( Marshaller, (IQuickSearchResultSnippet,), IMarshaller )

    def beforeTearDown(self):
        global search_results
        search_results = None
        gsm = getGlobalSiteManager()
        gsm.unregisterAdapter( Marshaller )
        gsm.unregisterAdapter( DummySearchSnippet )
        gsm.unregisterAdapter( DummyFacade )

        super(TestSearchRouter, self).beforeTearDown()

    def testGetLiveResults(self):
        global search_results
        search_results = [
            _createDummyResult(1, True)
            ]
        router = SearchRouter(self.dmd)
        varResults = router.getLiveResults( 'query' )

        self.assertEquals( {'results':
                            [_createJSONInfo(1, True)] },
                           varResults )

    def testMultipleGetLiveResults(self):
        global search_results
        search_results = [ _createDummyResult(x, False) for x in range(1,8)]
        router = SearchRouter(self.dmd)
        varResults = router.getLiveResults( 'query' )
        self.assertEquals( {'results':
                            [ _createJSONInfo(y, False) for y in range(1,8)]},
                           varResults )

    def testSanitizeQuery(self):
        cases = (('test', 'test'),
                 ('**zen**java**', 'zen*java'),
                 (' * * ***test***    * * test check  ', 'test check'))
        router = SearchRouter(self.dmd)
        for query, expected in cases:
            result = router._sanitizeQuery(query)
            self.assertEquals(result, expected)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSearchRouter))
    return suite
