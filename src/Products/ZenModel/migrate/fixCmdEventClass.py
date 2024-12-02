##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

__doc__="""The ZenPack ZenWinPerf had a "packable" relationship to several core
event classes. When the zenpack was removed it caused these classes to be removed.
This migrate script ensures that the classes exist and removes the packable relationship
from the ZenPack if it is still installed.
"""
import logging
import Migrate
from Products.ZenRelations.Exceptions import ObjectNotFound
log = logging.getLogger('zen.migrate')

class FixCmdEventClass(Migrate.Step):
    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        # make sure the following event classes exist.
        eventClasses = []
        paths = ('/Cmd', '/Cmd/Ok', '/Cmd/Fail', '/Conn', '/Conn/Fail')
        for path in paths:
            # createOrganizer will either create or return the existing event class
            eventClasses.append(dmd.Events.createOrganizer(path))

        # if ZenWinPerf is installed remove the classes from packable.
        try:
            pack = dmd.ZenPackManager.packs._getOb('ZenPacks.zenoss.ZenWinPerf')
            for ec in eventClasses:
                try:
                    pack.packables.removeRelation(ec)
                except ObjectNotFound:
                    log.debug("%s is not in the packable relationship for ZenWinPerf", ec)
        except AttributeError:
            log.debug("Skipping removing packable relationship because ZenWinPerf is not installed")

FixCmdEventClass()
