##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script integrates support for the ManagableIndex and
AdvancedQuery Products by removing old indexes and replacing them with
ManagableFieldIndex indices.
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError

from Products.ZenUtils.Search import makeFieldIndex
from Products.ZenUtils.Search import makeKeywordIndex

import Migrate

allCatalogs = {
    'Devices': {
        'componentSearch': ['meta_type', 'monitored'],
        'deviceSearch': ['id', 'summary'],
    },
    'Services': {
        'serviceSearch': ['serviceKeys'],
    },
    'Manufacturers': {
        'productSearch': ['productKeys'],
    },
    'Mibs': {
        'mibSearch': ['id', 'oid', 'summary'],
    },
    'Events': {
        'eventClassSearch': ['eventClassKey'],
    },
    'Networks': {
        'ipSearch': ['id'],
    },
}

keywordCatalogs = [
    'Manufacturers',
    'Mibs',
    'Services',
]

newModules = [
    'Products.ManagableIndex.FieldIndex',
    'Products.ManagableIndex.KeywordIndex',
]


class AdvancedQuery(Migrate.Step):

    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        # initialize our index tracker, in case catalogNames is empty
        indexed = {}
        for section, catalogNames in allCatalogs.items():
            # see which kind of index we need to create
            if section in keywordCatalogs:
                makeIndex = makeKeywordIndex
            else:
                makeIndex = makeFieldIndex
            for catalogName, indexNames in catalogNames.items():
                # we'll use a dict to keep track of whether this catalog will
                # need reindexing or not
                indexed = {}
                zcat = getattr(dmd.getDmdRoot(section), catalogName)
                cat = zcat._catalog
                # remove the lexicon, if it's there
                delID = 'myLexicon'
                try:
                    zcat._getOb(delID)
                    # delete the old lexicon
                    zcat._delOb(delID)
                    newObjs = []
                    for obj in zcat._objects:
                        if obj.get('id') != delID:
                            newObjs.append(obj)
                    zcat._objects = tuple(newObjs)
                    indexed[catalogName] = True
                except AttributeError:
                    # no lexicon found
                    indexed[catalogName] = False
                # replace the indices
                for indexName in indexNames:
                    if (catalogName == 'componentSearch' and 
                        indexName == 'monitored'):
                        # the monitored index contains bools, so we're not
                        # going to mess with it
                        indexed[catalogName] = False
                        continue
                    # check to see if the catalog is already using 
                    # ManagableIndex
                    module = cat.getIndex(indexName).__module__
                    if module in newModules:
                        indexed[catalogName] = False
                        continue
                    # get rid of the old index
                    try:
                        cat.delIndex(indexName)
                    except CatalogError:
                        pass
                    # add the new one
                    cat.addIndex(indexName, makeIndex(indexName))
                    indexed[catalogName] = True
            # reindex the current section
            if True in indexed.values():
                dmd.getDmdRoot(section).reIndex()

AdvancedQuery()
