##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018. All rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

log = logging.getLogger("zen.Reports")


class allheartbeatreport(object):
    def run(self, dmd, args):
        # ZEN-30539
        if args.get("adapt", ""):
            return []
        return dmd.ZenEventManager.getHeartbeatObjects(failures=False, limit=0)
