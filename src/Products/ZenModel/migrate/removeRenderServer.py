##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Render server is no longer used. Remove the object from the database.
"""

import logging
import Migrate

log = logging.getLogger("zen.migrate")

class RemoveRenderServer(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        zport = dmd.zport
        try:
            zport._delObject('RenderServer')
        except AttributeError:
            # it is already deleted
            pass


RemoveRenderServer()
