##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
import logging
log = logging.getLogger("zen.migrate")

class monitorAsHeartbeatDevice(Migrate.Step):
    """
    In version 2.3 we have changed the device component of heartbeat events to
    use the options.monitor value instead of socket.getfqdn(). This will result
    in heartbeat failures for all daemons upon upgrade to Zenoss 2.3.

    This script will automatically clear any heartbeats that aren't from a
    defined collector. This extra check makes it safe to re-run this migrate
    script on a 2.3+ instance without worrying about deleting heartbeats that
    shouldn't be deleted.
    """

    version = Migrate.Version(2, 3, 0)
    
    def cutover(self, dmd):
        log.info("Clearing heartbeats from devices that aren't collectors.")
        conn = dmd.ZenEventManager.connect()
        curr = conn.cursor()
        curr.execute("delete from heartbeat where device not in ('%s')" %
                "','".join(dmd.Monitors.getPerformanceMonitorNames()))

monitorAsHeartbeatDevice()
