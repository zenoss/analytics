##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate



class ClearPageCommand(Migrate.Step):
    "Clear default value for Page Command"

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):

        if getattr(dmd, "pageCommand", "").find("zensnpp") >= 0:
            dmd.pageCommand = ''
            log.info("Cleared default value for Page Command")

ClearPageCommand()
