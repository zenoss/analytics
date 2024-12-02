##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script removes case insensitivity from the catalogs that was
configured with the move to AdvancedQuery.
''' 

__version__ = "$Revision$"[11:-2]
        
import Migrate

from advanced_query import allCatalogs

caseSensitiveCatalogs = [
    'componentSearch',
    'eventClassSearch',
    'productSearch',
    'serviceSearch',
    ]

class CaseSensitive(Migrate.Step):

    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        # initialize our index tracker, in case catalogNames is empty
        indexed = {}
        for section, catalogNames in allCatalogs.items():
            for catalogName, indexNames in catalogNames.items():
                # we'll use a dict to keep track of whether this catalog will
                # need reindexing or not
                indexed = {}
                zcat = getattr(dmd.getDmdRoot(section), catalogName)
                cat = zcat._catalog
                # check to see if this needs to be a case-sensitive index
                if catalogName in caseSensitiveCatalogs:
                    prenormalizer = ''
                else:
                    prenormalizer = 'value/lower'
                    # check to see if it needs to be a keyword index
                # check the indices for a pre-normalizer attribute
                for indexName in indexNames:
                    idx = cat.getIndex(indexName)
                    if (hasattr(idx, 'PrenormalizeTerm') and 
                        idx.PrenormalizeTerm != prenormalizer):
                        idx.PrenormalizeTerm = prenormalizer
                        indexed[catalogName] = True
            # reindex the current section
            if True in indexed.values():
                dmd.getDmdRoot(section).reIndex()

CaseSensitive()
