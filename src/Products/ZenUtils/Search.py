##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Search

Utilities to help build zcatalog indexes
"""

from Products.ManagableIndex import FieldIndex, KeywordIndex
from Products.ZenUtils.ExtendedPathIndex import ExtendedPathIndex
from Products.ZenUtils.MultiPathIndex import MultiPathIndex

def makeCaseInsensitiveFieldIndex(indexName, termType='ustring'):
    index = FieldIndex(indexName)
    index.PrenormalizeTerm = 'value/lower'
    index.TermType = termType
    return index

def makeCaseInsensitiveKeywordIndex(indexName):
    index = KeywordIndex(indexName)
    index.PrenormalizeTerm = 'value/lower'
    index.TermType = 'ustring'
    index.TermTypeExtra = 'latin-1'
    return index

def makeCaseSensitiveKeywordIndex(indexName):
    index = KeywordIndex(indexName)
    index.TermType = 'ustring'
    index.TermTypeExtra = 'latin-1'
    return index

def makeCaseSensitiveFieldIndex(indexName):
    index = FieldIndex(indexName)
    index.TermType = 'ustring'
    return index

def makeFieldIndex(indexName):
    return makeCaseInsensitiveFieldIndex(indexName)

def makeKeywordIndex(indexName):
    return makeCaseInsensitiveKeywordIndex(indexName)

def makePathIndex(indexName):
    __pychecker__="no-abstract"
    return ExtendedPathIndex(indexName)

def makeMultiPathIndex(indexName):
    return MultiPathIndex(indexName)
