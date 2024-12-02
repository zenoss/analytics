##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Reexecute zenprocs.sql to get new version of procedures (now parameterized)
"""

from __future__ import absolute_import

import os
import Products.ZenEvents as _ze

from . import Migrate


class ProcParams(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        procs = os.path.join(os.path.dirname(_ze.__file__), "db/zenprocs.sql")
        os.system(  # noqa: S605
            "cat %s | mysql -u%s -p%s %s"
            % (
                procs,
                dmd.ZenEventManager.username,
                dmd.ZenEventManager.password,
                dmd.ZenEventManager.database,
            )
        )


ProcParams()
