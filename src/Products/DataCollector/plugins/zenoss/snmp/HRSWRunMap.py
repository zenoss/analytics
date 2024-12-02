##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2013 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# This file has 100% unit test coverage. If you modify it be sure to maintain
# the 100% test coverage.
#
# $ easy_install coverage
# $ coverage run /opt/zenoss/bin/runtests -m testHRSWRunMap
# $ coverage report -m DataCollector/plugins/zenoss/snmp/HRSWRunMap.py
# Name                                           Stmts   Miss  Cover   Missing
# ----------------------------------------------------------------------------
# DataCollector/plugins/zenoss/snmp/HRSWRunMap      70      0   100%

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)
from Products.ZenModel.OSProcessMatcher import buildObjectMapData

HRSWRUNENTRY = ".1.3.6.1.2.1.25.4.2.1"


class HRSWRunMap(SnmpPlugin):
    """Maps the processes running on the system to OSProcess objects.

    Uses the HOST-RESOURCES-MIB OIDs.
    """

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    deviceProperties = SnmpPlugin.deviceProperties + (
        "osProcessClassMatchData",
    )

    columns = {
        ".2": "_procName",
        ".4": "_procPath",
        ".5": "_parameters",
    }

    snmpGetTableMaps = (GetTableMap("hrSWRunEntry", HRSWRUNENTRY, columns),)

    def _extractProcessText(self, proc):
        path = proc.get("_procPath", "").strip()
        if path and path.find("\\") == -1:
            name = path
        else:
            name = proc.get("_procName", "").strip()
        if name:
            return unicode(
                (name + " " + proc.get("_parameters", "").strip()).rstrip(),
                errors="replace",
            )
        else:
            self._log.warn("Skipping process with no name")

    def process(self, device, results, log):
        """
        Process the SNMP information returned from a device
        """
        self._log = log
        log.info(
            "HRSWRunMap Processing %s for device %s", self.name(), device.id
        )
        getdata, tabledata = results
        log.debug("%s tabledata = %s", device.id, tabledata)

        # get the SNMP process data
        pidtable = tabledata.get("hrSWRunEntry")
        if pidtable is None:
            log.error(
                "Unable to get data for %s from hrSWRunEntry %s"
                " -- skipping model",
                HRSWRUNENTRY,
                device.id,
            )
            return None

        log.debug("=== Process information received ===")
        for p in sorted(pidtable.keys()):
            log.debug("snmpidx: %s\tprocess: %s", p, pidtable[p])

        if not pidtable.values():
            log.warning(
                "No process information from hrSWRunEntry %s", HRSWRUNENTRY
            )
            return None

        cmds = map(self._extractProcessText, pidtable.values())
        cmds = filter(lambda cmd: cmd, cmds)
        rm = self.relMap()
        matchData = device.osProcessClassMatchData
        rm.extend(map(self.objectMap, buildObjectMapData(matchData, cmds)))
        return rm
