##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""CmdBase

Add data base access functions for command line programs

$Id: ToManyRebuildKeys.py,v 1.2 2004/10/19 22:28:59 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import gc

from Acquisition import aq_parent

from Products.ZenUtils.Utils import getSubObjectsMemo

from ZCmdBase import ZCmdBase

from transaction import get_transaction

class ToManyRebuildKeys(ZCmdBase):

    def rebuild(self):
        ccount = 0
        for tomany in getSubObjectsMemo(self.dmd, self.filter, self.decend):
            self.log.debug("rebuilding keys for relation %s on object %s",
                           tomany.getId(), aq_parent(tomany).getId())
            ccount += tomany.rebuildKeys(self.log)
            if ccount >= self.options.commitCount and not self.options.noCommit:
                trans = get_transaction()
                trans.note('ToManyRebuildKeys rebuilt keys')
                trans.commit()
                ccount = 0
                self.dmd._p_jar.sync()
                gc.collect()
        if self.options.noCommit:
            self.log.info("not commiting any changes")
        else:
            trans = get_transaction()
            trans.note('ToManyRebuildKeys rebuilt keys')
            trans.commit()


    def filter(self, obj):
        return obj.meta_type == "To Many Relationship"


    def decend(self, obj):
        from Products.ZenModel.ZenModelRM import ZenModelRM
        from Products.ZenRelations.ToManyRelationship \
            import ToManyRelationship
        return (isinstance(obj, ZenModelRM) or 
                isinstance(obj, ToManyRelationship))


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=1000,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


if __name__ == "__main__":
    tmbk = ToManyRebuildKeys()
    tmbk.rebuild()
