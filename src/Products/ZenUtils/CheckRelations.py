##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import transaction

from Products.ZenUtils.Utils import getAllConfmonObjects
from Products.ZenUtils.ZenScriptBase import ZenScriptBase


class CheckRelations(ZenScriptBase):

    def rebuild(self):
        repair = self.options.repair
        ccount = 0
        self.log.info("Checking relations...")
        for object in getAllConfmonObjects(self.dmd):
            ccount += 1
            self.log.debug(
                "checking relations on object %s", object.getPrimaryDmdId()
            )
            object.checkRelations(repair=repair)
            ch = object._p_changed
            if not ch:
                object._p_deactivate()
            if ccount >= self.options.savepoint:
                transaction.savepoint()
                ccount = 0
        if self.options.nocommit:
            self.log.info("not commiting any changes")
        else:
            trans = transaction.get()
            trans.note("CheckRelations cleaned relations")
            trans.commit()

    def buildOptions(self):
        super(CheckRelations, self).buildOptions()

        self.parser.add_option(
            "-r",
            "--repair",
            dest="repair",
            action="store_true",
            help="repair all inconsistant relations",
        )
        self.parser.add_option(
            "-x",
            "--savepoint",
            dest="savepoint",
            default=500,
            type="int",
            help="how many lines should be loaded before savepoint",
        )
        self.parser.add_option(
            "-n",
            "--nocommit",
            dest="nocommit",
            action="store_true",
            help="Do not store changes to the Dmd (for debugging)",
        )


def main():
    CheckRelations(connect=True).rebuild()
