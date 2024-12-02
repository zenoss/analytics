##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
add zNoRelationshipCopy property for devices 
"""

import logging
import Migrate

log = logging.getLogger("zen.migrate")


class addzNoRelationshipCopy(Migrate.Step):
    version = Migrate.Version(200, 7, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Devices, "zNoRelationshipCopy"):
            dmd.Devices._setProperty("zNoRelationshipCopy", ["pack"], type="lines")


addzNoRelationshipCopy()
