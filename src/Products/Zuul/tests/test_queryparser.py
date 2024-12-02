##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os.path
from zope.interface import providedBy

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.Zuul.search.interfaces import ISearchQueryParser
from Products.Zuul.search.interfaces import IParsedQuery
from Products.Zuul.search.facades import ParsedQuery
from Products.Zuul.search.facades import DefaultQueryParser

import logging
log = logging.getLogger("zen.search")



class TestQueryParser(BaseTestCase):

    def testParsedQuery(self):
        operators = {'type':['events','devices','puddingpops'],
                     'op2':['nuttin','honey']}
        keywords = ['dont','look','now']
        pq = ParsedQuery( operators, keywords )
        self.assert_( IParsedQuery in providedBy( pq ) )
        self.assertEquals( operators, pq.operators )
        self.assertEquals( keywords, pq.keywords )

    def testDefaultQueryParser(self):
        qp = DefaultQueryParser()
        self.assert_( ISearchQueryParser in providedBy( qp ) )
        self._assertParseEquals( qp, "",
            {}, [] )
        self._assertParseEquals( qp, "a b c d",
            {}, ['a','b','c','d'] )
        self._assertParseEquals( qp, "type:1",
            {'type':['1']}, [] )
        self._assertParseEquals( qp, "type:",
            {'type':['']}, [] )
        self._assertParseEquals( qp, "type:1 size:2",
            {'type':['1'],'size':['2']}, [] )
        self._assertParseEquals( qp, "type:1 type:2",
            {'type':['1','2']},[] )
        self._assertParseEquals( qp, "a b type:2 c",
            {'type':['2']}, ['a','b','c'] )
        self._assertParseEquals( qp, "type:4 a b type:2 c size:1 d",
            {'type':['4','2'],'size':['1']}, ['a','b','c','d'] )

    def _assertParseEquals(self, queryParser, queryString,
                           expectedOperators, expectedKeywords ):
        results = queryParser.parse( queryString )
        qpOps = results.operators
        qpKws = results.keywords
        self._assertListEquals( qpOps.keys(), expectedOperators.keys() )
        for key, values in expectedOperators.iteritems():
            self._assertListEquals( values, qpOps[key] )

        self._assertListEquals( expectedKeywords, qpKws )

    def _assertListEquals(self, control, variable ):
        self.assert_( isinstance( control, list ) and
                      isinstance( variable, list ),
                      '_assertListEquals takes only lists' )
        newControl = control[:]
        newVariable = variable[:]
        newControl.sort()
        newVariable.sort()
        self.assertEquals( newControl, newVariable )


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestQueryParser))
    return suite
