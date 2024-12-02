##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate

from Products.ZenUtils.ShardedBTree import ShardedBTree
from Products.ZenUtils.guid.guid import GUID_TABLE_PATH, DEFAULT_NUMBER_OF_SHARDS


class ShardGuidTable(Migrate.Step):
    version = Migrate.Version(200, 0, 1)

    def cutover(self, dmd):
        old_table = dmd.unrestrictedTraverse(GUID_TABLE_PATH)
        if not isinstance(old_table, ShardedBTree):
            # get table parent and name
            splitted_path = GUID_TABLE_PATH.split("/")
            table_parent = dmd.unrestrictedTraverse(splitted_path[:-1])
            table_name = splitted_path[-1]
            # create sharded table
            sharded_tree = ShardedBTree(n_shards=DEFAULT_NUMBER_OF_SHARDS)
            sharded_tree.update(old_table)
            # replace the old table
            table_parent._delOb(table_name)
            table_parent._setObject(table_name, sharded_tree)


ShardGuidTable()
