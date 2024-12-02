##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''

Convert 4.x-style DistributedPerformanceConf localhost hub + collector to
a 5.x-style one.

'''
import Migrate
import logging

log = logging.getLogger('zen.migrate')

class MigrateLocalhostPerf(Migrate.Step):
    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            from ZenPacks.zenoss.DistributedCollector import \
                addHubRoot, addLocalhostHub, convertLocalhostHubToCC, convertAllMonitors, \
                convertMonitor, convertLocalhostMonitorToCC
        except ImportError:
            log.info("Distributed collector module not found, skipping")
        else:
            log.info("Migrating localhost hub + monitor")
            # Assume localhost hub + collector exist
            root = dmd.Monitors
            hubRoot = root.get('Hub')
            # No DC-style Performance dmd path yet.  Shouldn't really ever hit this,
            # because zenpack install should take care of this.  If hit, then
            # exit.
            if not hubRoot:
                return

            localhostHub = hubRoot.get('localhost')
            if not localhostHub:
                log.info("Unable to find localhost hub, creating now")
                localhostHub = addLocalhostHub(hubRoot)

            localhostHubccBacked = getattr(localhostHub, 'ccBacked')
            if not localhostHubccBacked:
                log.info("Upgrading localhost hub to be control center-backed")
                # convert already DC-upgraded hub to be 5.x-compat
                convertLocalhostHubToCC(localhostHub)

            localhostMonitor = root.Performance.get('localhost')
            localhostMonitorccBacked = getattr(localhostMonitor, 'ccBacked')
            if not localhostMonitorccBacked:
                log.info("Upgrading localhost monitor to be control center-backed")
                convertLocalhostMonitorToCC(localhostMonitor)

MigrateLocalhostPerf()
