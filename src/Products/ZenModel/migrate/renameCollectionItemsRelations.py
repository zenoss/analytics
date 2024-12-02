##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Acquisition import aq_base
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship

class renameCollectionItemsRelations(Migrate.Step):
    version = Migrate.Version(3, 0, 0)
    
    def cutover(self, dmd):
        reportclass = dmd.Reports._getOb('Multi-Graph Reports')
        for report in reportclass.reports():

            # if this item does not have a 'collections' attribute
            # go on to the next
            try:
                rptcolls = report.collections
            except AttributeError:
                continue
                
            # for every collection attached to this report,
            # change the 'items' relation to 'collection_items'
            for coll in rptcolls():
                rel = coll.items
                if isinstance(rel, ToManyContRelationship):
                    obs = []
                    for ob in rel():
                        obs.append(aq_base(ob))
                        remote_rel = ob.collection
                        remote_rel._remove(coll)
                        rel._remove(ob)
                    coll._delObject('items')
                    coll.buildRelations()
                    newrel = coll.collection_items.primaryAq()
                    for ob in obs:
                        newrel._setObject(ob.getId(), ob)
                        ob = newrel._getOb(ob.getId())
                        assert ob.__primary_parent__ == newrel
                        assert ob.collection() == coll
                        assert ob in newrel()

renameCollectionItemsRelations()
