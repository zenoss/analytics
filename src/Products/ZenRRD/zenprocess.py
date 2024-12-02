#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zenprocess

Gets SNMP process data from a device's HOST-RESOURCES-MIB
and store process performance in RRD files.
"""

import logging
import sys
import os.path

from pprint import pformat

import six
import zope.component
import zope.interface

from pynetsnmp.twistedsnmp import SnmpUsmError
from twisted.internet import defer, error

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import (
    ICollectorPreferences,
    IConfigurationListener,
    IDataService,
    IEventService,
    IScheduledTask,
)
from Products.ZenCollector.tasks import (
    SimpleTaskFactory,
    SimpleTaskSplitter,
    TaskStates,
)
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import (
    Status_OSProcess,
    Status_Perf,
    Status_Snmp,
)
from Products.ZenModel.OSProcessMatcher import OSProcessMatcher
from Products.ZenModel.OSProcessState import determineProcessState
from Products.ZenUtils.observable import ObservableMixin

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. DeviceProxy.
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.ProcessConfig import ProcessProxy
from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
from Products.ZenUtils.Utils import unused

unused(DeviceProxy, ProcessProxy, SnmpConnInfo)

COLLECTOR_NAME = "zenprocess"

log = logging.getLogger("zen.{}".format(COLLECTOR_NAME))

# HOST-RESOURCES-MIB OIDs used
HOSTROOT = ".1.3.6.1.2.1.25"
RUNROOT = HOSTROOT + ".4"
NAMETABLE = RUNROOT + ".2.1.2"
PATHTABLE = RUNROOT + ".2.1.4"
ARGSTABLE = RUNROOT + ".2.1.5"
PERFROOT = HOSTROOT + ".5"
CPU = PERFROOT + ".1.1.1."  # note trailing dot
MEM = PERFROOT + ".1.1.2."  # note trailing dot

# Max size for CPU numbers
WRAP = 0xFFFFFFFF

PROC_SCAN_ERROR = "Unable to read processes on device %s"

RESOURCE_MIB = "resource_mib"
SNMP_CONFIG_ERROR = "snmp_config_error"
TABLE_SCAN_TIMEOUT = "table_scan_timeout"
TABLE_SCAN_V3_ERROR = "table_scan_v3_error"
PROCESS_STATUS = "process_status"


class HostResourceMIBException(Exception):
    pass


# Create an implementation of the ICollectorPreferences interface so that the
# ZenCollector framework can configure itself from our preferences.
class ZenProcessPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new ZenProcessPreferences instance and provide default
        values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.configCycleInterval = 20  # minutes

        # will be updated based on Performance Config property of same name
        self.processCycleInterval = 3 * 60

        # will be filled in based on buildOptions
        self.options = None

        # the configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = "Products.ZenHub.services.ProcessConfig"

    @property
    def cycleInterval(self):
        """
        defined as a property since it is needed by the interface
        """
        return self.processCycleInterval

    def buildOptions(self, parser):
        """
        Build a list of command-line options
        """
        parser.add_option(
            "--showprocs",
            dest="showprocs",
            action="store_true",
            default=False,
            help="Show the list of processes found."
            "For debugging purposes only.",
        )
        parser.add_option(
            "--showrawtables",
            dest="showrawtables",
            action="store_true",
            default=False,
            help="Show the raw SNMP processes data returned "
            "from the device. For debugging purposes only.",
        )
        parser.add_option(
            "--captureFilePrefix",
            dest="captureFilePrefix",
            default="",
            help="Directory and filename to use as a template"
            " to store SNMP results from device.",
        )

    def postStartup(self):
        pass


class DeviceStats:
    def __init__(self, deviceProxy):
        self.config = deviceProxy
        # map pid number to ProcessStats object
        self._pidToProcess = {}
        # map ProcessProxy id to ProcessStats object
        self._processes = {}
        for id, process in deviceProxy.processes.iteritems():
            self._processes[id] = ProcessStats(process)

    def update(self, deviceProxy):
        unused = set(self._processes)
        for id, process in deviceProxy.processes.iteritems():
            unused.discard(id)
            if id in self._processes:
                self._processes[id].update(process)
            else:
                self._processes[id] = ProcessStats(process)

        # delete the left overs
        for id in unused:
            del self._processes[id]
            for key, value in self._pidToProcess.items():
                if value._config.name == id:
                    del self._pidToProcess[key]

    @property
    def processStats(self):
        """
        returns an iterator of the processes configured to be monitored
        """
        return self._processes.itervalues()

    @property
    def pids(self):
        """
        returns an iterator of the pids being tracked
        """
        return self._pidToProcess.iterkeys()

    @property
    def monitoredProcs(self):
        """
        returns an iterator of ProcessStats for which we have a pid
        """
        return self._pidToProcess.itervalues()


class ProcessStats(OSProcessMatcher):
    def __init__(self, processProxy):
        self._pids = {}
        self.cpu = 0
        self.update(processProxy)

    def update(self, processProxy):
        self._config = processProxy
        self.includeRegex = self._config.includeRegex
        self.excludeRegex = self._config.excludeRegex
        self.replaceRegex = self._config.replaceRegex
        self.replacement = self._config.replacement
        self.primaryUrlPath = self._config.processClassPrimaryUrlPath()
        self.generatedId = self._config.generatedId

    def processClassPrimaryUrlPath(self):
        return self.primaryUrlPath

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return str(self._config.name)

    __repr__ = __str__

    def updateCpu(self, pid, value):
        """ """
        pid = self._pids.setdefault(pid, Pid())
        cpu = pid.updateCpu(value)
        if cpu is not None:
            self.cpu += cpu
            self.cpu %= WRAP

    def getCpu(self):
        """ """
        return self.cpu

    def updateMemory(self, pid, value):
        """ """
        self._pids.setdefault(pid, Pid()).memory = value

    def getMemory(self):
        """ """
        return sum(
            x.memory for x in self._pids.itervalues() if x.memory is not None
        )

    def discardPid(self, pid):
        """ """
        if pid in self._pids:
            del self._pids[pid]

    def _sync_pids(self, pids):
        """
        Removes PIDs that are no longer related to current process.

        @parameter pids: iterable with PIDs that are related to current process
        """
        self._pids = {k: v for k, v in self._pids.iteritems() if k in pids}


class Pid:
    """
    Helper class to track process id information
    """

    cpu = None
    memory = None

    def updateCpu(self, n):
        """ """
        if n is not None:
            try:
                n = int(n)
            except ValueError:
                log.warning("Bad value for CPU: '%s'", n)

        if self.cpu is None or n is None:
            self.cpu = n
            return None
        diff = n - self.cpu
        if diff < 0:
            # don't provide a value when the counter falls backwards
            n = None
            diff = None
        self.cpu = n
        return diff

    def updateMemory(self, n):
        """ """
        self.memory = n

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return "<Pid> memory: %s cpu: %s" % (self.memory, self.cpu)

    __repr__ = __str__


class ConfigListener(object):
    zope.interface.implements(IConfigurationListener)

    def deleted(self, configurationId):
        """
        Called when a configuration is deleted from the collector
        """
        log.debug("ConfigListener: configuration %s deleted", configurationId)
        ZenProcessTask.DEVICE_STATS.pop(configurationId, None)

    def added(self, configuration):
        """
        Called when a configuration is added to the collector
        """
        log.debug("ConfigListener: configuration %s added", configuration)

    def updated(self, newConfiguration):
        """
        Called when a configuration is updated in collector
        """
        log.debug("ConfigListener: configuration %s updated", newConfiguration)


# Create an implementation of the IScheduledTask interface that will perform
# the actual collection work needed by this collector.
class ZenProcessTask(ObservableMixin):
    """
    A scheduled task that finds instances of configure processes and collects
    metrics on the processes
    """

    zope.interface.implements(IScheduledTask)

    # Keep state about process stats across task updates
    DEVICE_STATS = {}

    # counter to keep track of total restarted and missing processes
    RESTARTED = 0
    MISSING = 0

    STATE_CONNECTING = "CONNECTING"
    STATE_SCANNING_PROCS = "SCANNING_PROCESSES"
    STATE_FETCH_PERF = "FETCH_PERF_DATA"
    STATE_STORE_PERF = "STORE_PERF_DATA"
    STATE_PARSING_TABLE_DATA = "PARSING_TABLE_DATA"

    statusEvent = {"eventClass": Status_OSProcess, "eventGroup": "Process"}

    def __init__(
        self, deviceId, taskName, scheduleIntervalSeconds, taskConfig
    ):
        super(ZenProcessTask, self).__init__()

        # needed for interface
        self.name = taskName
        self.configId = deviceId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE

        # the task config corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = self._device.name
        self._manageIp = self._device.manageIp
        self._maxOidsPerRequest = self._device.zMaxOIDPerRequest

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = zope.component.queryUtility(
            ICollectorPreferences, COLLECTOR_NAME
        )
        self._snmpStatusEvent = dict(
            self.statusEvent,
            agent=COLLECTOR_NAME,
            device=self._devId,
            eventClass=Status_Snmp,
        )
        self.snmpProxy = None
        self.snmpConnInfo = self._device.snmpConnInfo

        self._deviceStats = ZenProcessTask.DEVICE_STATS.get(self._devId)
        if self._deviceStats:
            self._deviceStats.update(self._device)
        else:
            self._deviceStats = DeviceStats(self._device)
            ZenProcessTask.DEVICE_STATS[self._devId] = self._deviceStats

    @defer.inlineCallbacks
    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: job to scan a device
        @rtype: Twisted deferred object
        """
        try:
            # see if we need to connect first before doing any collection
            try:
                self.openProxy()
                self._clearSnmpError(
                    "SNMP config error cleared", SNMP_CONFIG_ERROR
                )
            except Exception as ex:
                log.error("failed to create SNMP session: %s", ex)
                self._sendSnmpError(
                    "SNMP config error: {}".format(ex), SNMP_CONFIG_ERROR
                )
            else:
                log.debug(
                    "opened proxy to %s [%s]", self._devId, self._manageIp
                )
                yield self._collectCallback()
        finally:
            self._finished()

    @defer.inlineCallbacks
    def _collectCallback(self):
        """
        Callback called after a connect or previous collection so that another
        collection can take place.
        """
        log.debug(
            "Scanning for processes from %s [%s]", self._devId, self._manageIp
        )

        self.state = ZenProcessTask.STATE_SCANNING_PROCS
        tables = [NAMETABLE, PATHTABLE, ARGSTABLE]
        try:
            tableResult = yield self._getTables(tables)
            summary = "Process table up for device %s" % self._devId
            self._clearSnmpError(
                "%s - timeout cleared" % summary, TABLE_SCAN_TIMEOUT
            )
            if self.snmpConnInfo.zSnmpVer == "v3":
                self._clearSnmpError(
                    "%s - v3 error cleared" % summary, TABLE_SCAN_V3_ERROR
                )

            processes = self._parseProcessNames(tableResult)
            self._clearSnmpError(summary, RESOURCE_MIB)
            self._deviceStats.update(self._device)
            processStatuses = self._determineProcessStatus(processes)
            self._sendProcessEvents(processStatuses)
            self._clearSnmpError(summary, PROCESS_STATUS)
            yield self._fetchPerf()
            log.debug(
                "Device %s [%s] scanned successfully",
                self._devId,
                self._manageIp,
            )
        except HostResourceMIBException:
            summary = (
                "Device %s does not publish HOST-RESOURCES-MIB" % self._devId
            )
            resolution = "Verify with snmpwalk %s %s" % (
                self._devId,
                NAMETABLE,
            )
            log.warn(summary)
            self._sendSnmpError(summary, RESOURCE_MIB, resolution=resolution)
        except error.TimeoutError:
            log.debug("Timeout fetching tables on device %s", self._devId)
            self._sendSnmpError(
                "%s; Timeout on device" % (PROC_SCAN_ERROR % self._devId,),
                TABLE_SCAN_TIMEOUT,
            )
        except SnmpUsmError as e:
            msg = (
                "Cannot connect to SNMP agent on {0._devId}: {1}".format(
                    self, e
                )
            )
            log.debug(msg)
            self._sendSnmpError(
                "%s; %s" % (PROC_SCAN_ERROR % self._devId, msg),
                TABLE_SCAN_V3_ERROR,
            )
        except Exception as e:
            log.exception("Unexpected Error on device %s", self._devId)
            msg = "%s; error: %s" % (PROC_SCAN_ERROR % self._devId, e)
            self._sendSnmpError(msg, PROCESS_STATUS)

    def _finished(self):
        """
        Callback activated when the task is complete
        """
        try:
            self._close()
        except Exception as e:
            log.warn("Failed to close device %s: error %s", self._devId, e)

    def cleanup(self):
        return self._close()

    def capturePacket(self, hostname, data):
        """
        Store SNMP results into files for unit-testing.
        """
        # Prep for using capture replay module later
        if not hasattr(self, "captureSerialNum"):
            self.captureSerialNum = 0

        log.debug("Capturing packet from %s", hostname)
        name = "%s-%s-%d" % (
            self._preferences.options.captureFilePrefix,
            hostname,
            self.captureSerialNum,
        )

        # Don't overwrite previous captures, which will happen if we remodel
        # and the serial number gets reset to zero
        while os.path.exists(name):
            self.captureSerialNum += 1
            name = "%s-%s-%d" % (
                self._preferences.options.captureFilePrefix,
                hostname,
                self.captureSerialNum,
            )

        try:
            with open(name, "w") as capFile:
                capFile.write(pformat(data))
            self.captureSerialNum += 1
        except Exception as ex:
            log.warn(
                "Couldn't write capture data to '%s' because %s", name, str(ex)
            )

    def sendRestartEvents(self, afterByConfig, beforeByConfig, restarted):
        for procStats, pConfig in restarted.iteritems():
            droppedPids = []
            for pid in beforeByConfig[procStats]:
                if pid not in afterByConfig[procStats]:
                    droppedPids.append(pid)
            procClassName = pConfig.processClass.rsplit("/", 1)[-1]
            summary = (
                "Process(es) restarted in process set: %s" % procClassName
            )
            message = (
                "%s\n Using regex '%s' "
                "Discarded dead pid(s) %s "
                "Using new pid(s) %s"
            ) % (
                summary,
                pConfig.includeRegex,
                droppedPids,
                afterByConfig[procStats],
            )
            self._eventService.sendEvent(
                self.statusEvent,
                device=self._devId,
                summary=summary,
                message=message,
                component=pConfig.originalName,
                eventKey=pConfig.processClass,
                severity=pConfig.severity,
            )
            log.info("(%s) %s", self._devId, message)

    def sendFoundProcsEvents(self, afterByConfig, restarted):
        # report alive processes
        for processStat, pids in afterByConfig.iteritems():
            if processStat in restarted:
                continue
            procClassName = processStat._config.processClass.rsplit("/", 1)[-1]
            summary = "Process up: %s" % procClassName
            message = "%s\n Using regex '%s' with pid's %s " % (
                summary,
                processStat._config.includeRegex,
                pids,
            )
            self._eventService.sendEvent(
                self.statusEvent,
                device=self._devId,
                summary=summary,
                message=message,
                component=processStat._config.originalName,
                eventKey=processStat._config.processClass,
                severity=Event.Clear,
            )
            log.debug("(%s) %s", self._devId, message)

    def _parseProcessNames(self, results):
        """
        Parse the process tables and reconstruct the list of processes
        that are on the device.

        @parameter results: results of SNMP table gets
        @type results: dictionary of dictionaries
        """
        self.state = ZenProcessTask.STATE_PARSING_TABLE_DATA
        if not results or not results[NAMETABLE]:
            raise HostResourceMIBException()

        if self._preferences.options.captureFilePrefix:
            self.capturePacket(self._devId, results)

        showrawtables = self._preferences.options.showrawtables
        procs = mapResultsToDicts(showrawtables, results)

        if self._preferences.options.showprocs:
            self._showProcessList(procs)
        return procs

    def sendMissingProcsEvents(self, missing):
        # Look for missing processes
        for procConfig in missing:
            ZenProcessTask.MISSING += 1
            procClassName = procConfig.processClass.rsplit("/", 1)[-1]
            summary = (
                "Process set contains 0 running processes: %s" % procClassName
            )
            message = (
                "%s\n   "
                "Using regex '%s' \n   "
                "All Processes have stopped since the last model occurred. "
                "Last Modification time (%s)"
            ) % (
                summary,
                procConfig.includeRegex,
                self._device.lastmodeltime,
            )
            dedupList = [
                self._devId,
                procConfig.generatedId,
                self.statusEvent["eventClass"],
                procConfig.processClass,
                str(procConfig.severity),
            ]
            dedupid = "|".join(dedupList)
            self._eventService.sendEvent(
                self.statusEvent,
                device=self._devId,
                summary=summary,
                message=message,
                dedupid=dedupid,
                component=procConfig.originalName,
                eventKey=procConfig.processClass,
                severity=procConfig.severity,
            )
            log.warning("(%s) %s", self._devId, message)

    def _sendProcessEvents(self, results):
        (
            afterByConfig,
            afterPidToProcessStats,
            beforeByConfig,
            newPids,
            restarted,
            deadPids,
            missing,
        ) = results

        self.sendRestartEvents(afterByConfig, beforeByConfig, restarted)
        self.sendFoundProcsEvents(afterByConfig, restarted)

        for pid in newPids:
            log.debug(
                "Found new %s %s pid %d on %s ",
                afterPidToProcessStats[pid]._config.originalName,
                afterPidToProcessStats[pid]._config.name,
                pid,
                self._devId,
            )
        self._deviceStats._pidToProcess = afterPidToProcessStats
        self.sendMissingProcsEvents(missing)

        # Store the total number of each process into an RRD
        pidCounts = {p: 0 for p in self._deviceStats.processStats}

        for procStat in self._deviceStats.monitoredProcs:
            # monitoredProcs is determined from the current pids in
            # _pidToProcess. pidCounts is from _deviceStats.processStats
            # which is modeled data.
            if procStat in pidCounts:
                pidCounts[procStat] += 1
            else:
                log.warn(
                    "%s monitored proc %s %s not in process stats",
                    self._devId,
                    procStat._config.name,
                    procStat._config.originalName,
                )
                log.debug("%s pidcounts is %s", self._devId, pidCounts)
        for procName, count in pidCounts.iteritems():
            self._save(procName, "count_count", count, "GAUGE")
        return "Sent events"

    def _determineProcessStatus(self, procs):
        """
        Determine the up/down/restarted status of processes.

        @parameter procs: array of pid, (name_with_args) info
        @type procs: list
        @parameter deviceStats:
        @type procs:
        """
        afterPidToProcessStats = {}

        for pid, name_with_args in procs:
            log.debug("pid: %s --- name_with_args: %s", pid, name_with_args)
            for pStats in self._deviceStats.processStats:
                if pStats._config.name is not None:
                    if pStats.matches(name_with_args):
                        log.debug(
                            "Found process %s belonging to %s",
                            name_with_args,
                            pStats._config,
                        )
                        afterPidToProcessStats[pid] = pStats
                        break

        afterByConfig = reverseDict(afterPidToProcessStats)

        restarted = {}
        (deadPids, restartedPids, newPids) = determineProcessState(
            reverseDict(self._deviceStats._pidToProcess), afterByConfig
        )

        restarted = {}
        for restartedPid in restartedPids:
            ZenProcessTask.RESTARTED += 1
            procStats = afterPidToProcessStats[restartedPid]
            pConfig = procStats._config

            # only if configured to alert on restarts...
            if pConfig.restart:
                restarted[procStats] = pConfig

        # populate missing (the process set contains 0 processes...)
        missing = []
        for procStat in self._deviceStats.processStats:
            if procStat not in afterByConfig:
                missing.append(procStat._config)

        # For historical reasons, return the beforeByConfig
        beforeByConfig = reverseDict(self._deviceStats._pidToProcess)

        return (
            afterByConfig,
            afterPidToProcessStats,
            beforeByConfig,
            newPids,
            restarted,
            deadPids,
            missing,
        )

    @defer.inlineCallbacks
    def _fetchPerf(self):
        """
        Get performance data for all the monitored processes on a device
        """
        self.state = ZenProcessTask.STATE_FETCH_PERF

        oids = []
        for pid in self._deviceStats.pids:
            oids.extend([CPU + str(pid), MEM + str(pid)])
        if oids:
            singleOids = set()
            results = {}
            oidsToTest = oids
            chunkSize = self._maxOidsPerRequest
            while oidsToTest:
                for oidChunk in chunk(oidsToTest, chunkSize):
                    try:
                        log.debug(
                            "%s fetching oid(s) %s", self._devId, oidChunk
                        )
                        result = yield self._get(oidChunk)
                        results.update(result)
                    except (error.TimeoutError, SnmpUsmError) as e:
                        log.debug("error reading oid(s) %s - %s", oidChunk, e)
                        singleOids.update(oidChunk)
                oidsToTest = []
                if singleOids and chunkSize > 1:
                    chunkSize = 1
                    log.debug(
                        "running oids for %s in single mode %s",
                        self._devId,
                        singleOids,
                    )
                    oidsToTest = list(singleOids)
            self._storePerfStats(results)

    def _storePerfStats(self, results):
        """
        Save the process performance data in RRD files

        @parameter results: results of SNMP table gets
        @type results: dict of {oid:value} dictionaries
        """
        self.state = ZenProcessTask.STATE_STORE_PERF
        byConf = reverseDict(self._deviceStats._pidToProcess)
        for procStat, pids in byConf.iteritems():
            if len(pids) != 1:
                log.debug(
                    "There are %d pids by the name %s - %s",
                    len(pids),
                    procStat._config.name,
                    procStat._config.originalName,
                )
            procName = procStat
            procStat._sync_pids(pids)
            for pid in pids:
                cpu = results.get(CPU + str(pid), None)
                mem = results.get(MEM + str(pid), None)
                procStat.updateCpu(pid, cpu)
                procStat.updateMemory(pid, mem)
            self._save(procName, "cpu_cpu", procStat.getCpu(), "DERIVE", min=0)
            self._save(
                procName, "mem_mem", procStat.getMemory() * 1024, "GAUGE"
            )
        return results

    def _getTables(self, oids):
        """
        Perform SNMP getTable for specified OIDs

        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        repetitions = self._maxOidsPerRequest / len(oids)
        t = self.snmpProxy.getTable(
            oids,
            timeout=self.snmpConnInfo.zSnmpTimeout,
            retryCount=self.snmpConnInfo.zSnmpTries,
            maxRepetitions=repetitions,
            limit=sys.maxint,
        )
        return t

    def _get(self, oids):
        """
        Perform SNMP get for specified OIDs

        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        return self.snmpProxy.get(
            oids, self.snmpConnInfo.zSnmpTimeout, self.snmpConnInfo.zSnmpTries
        )

    def openProxy(self):
        """
        Create a connection to the remote device
        """
        self.state = ZenProcessTask.STATE_CONNECTING
        if (
            self.snmpProxy is None
            or self.snmpProxy.snmpConnInfo != self.snmpConnInfo
        ):
            try:
                self.snmpProxy = self.snmpConnInfo.createSession()
                self.snmpProxy.open()
            except Exception:
                self.snmpProxy = None
                raise

    def _close(self):
        """
        Close down the connection to the remote device
        """
        if self.snmpProxy:
            self.snmpProxy.close()
        self.snmpProxy = None

    def _showProcessList(self, procs):
        """
        Display the processes in a sane manner.

        @parameter procs: list of (pid, name_with_args)
        @type procs: list of tuples
        """
        device_name = self._devId
        proc_list = [
            "%s %s" % (pid, name_with_args)
            for pid, name_with_args in sorted(procs)
        ]
        proc_list.append("")
        log.info(
            "#===== Processes on %s:\n%s", device_name, "\n".join(proc_list)
        )

    def _sendSnmpError(self, message, eventKey, **kwargs):
        event = self._snmpStatusEvent.copy()
        event.update(kwargs)
        self._eventService.sendEvent(
            event, eventKey=eventKey, severity=Event.Error, summary=message
        )

    def _clearSnmpError(self, message, eventKey):
        """
        Send an event to clear other events.

        @parameter message: clear text
        @type message: string
        """
        self._eventService.sendEvent(
            self._snmpStatusEvent,
            eventKey=eventKey,
            severity=Event.Clear,
            summary=message,
        )

    def _save(self, pidName, statName, value, rrdType, min="U"):
        """
        Save a value into an RRD file

        @param pidName: process id of the monitored process
        @type pidName: string
        @param statName: metric name
        @type statName: string
        @param value: data to be stored
        @type value: number
        @param rrdType: Metric data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        """
        metadata = pidName._config.metadata
        try:
            self._dataService.writeMetricWithMetadata(
                statName, value, rrdType, min=min, metadata=metadata
            )
        except Exception as ex:
            summary = "Unable to save data for process-monitor metric %s" % (
                metadata.get("contextKey")
            )
            log.critical(summary)

            message = "Data was value= %s, type=%s" % (value, rrdType)
            log.critical(message)
            log.exception(ex)

            import traceback

            trace_info = traceback.format_exc()

            self._eventService.sendEvent(
                {
                    "dedupid": "{0.options.monitor}|{1}".format(
                        self._preferences, "Metric write failure"
                    ),
                    "severity": Event.Critical,
                    "device": self._preferences.options.monitor,
                    "eventClass": Status_Perf,
                    "component": "METRIC",
                    "pidName": pidName,
                    "statName": statName,
                    "message": message,
                    "traceback": trace_info,
                    "summary": summary,
                }
            )


def mapResultsToDicts(showrawtables, results):
    """
    Parse the process tables and reconstruct the list of processes
    that are on the device.

    @parameter showrawtables: log the raw table info?
    @type showrawtables: boolean
    @parameter results: results of SNMP table gets ie (OID + pid, value)
    @type results: dictionary of dictionaries
    @return: maps relating names and pids to each other
    @rtype: list of tuples
    """

    def extract(dictionary, oid, value):
        """
        Helper function to extract SNMP table data.
        """
        pid = int(oid.rsplit(".", 1)[-1])
        dictionary[pid] = value.strip()

    names, paths, args = {}, {}, {}
    if showrawtables:
        log.info("NAMETABLE = %r", results[NAMETABLE])
    for row in results[NAMETABLE].iteritems():
        extract(names, *row)

    if showrawtables:
        log.info("PATHTABLE = %r", results[PATHTABLE])
    for row in results[PATHTABLE].iteritems():
        extract(paths, *row)

    if showrawtables:
        log.info("ARGSTABLE = %r", results[ARGSTABLE])
    for row in results[ARGSTABLE].iteritems():
        extract(args, *row)

    procs = []
    for pid, name in names.iteritems():
        path = paths.get(pid, "")
        if path and path.find("\\") == -1:
            name = path
        arg = six.text_type(args.get(pid, ""), errors="replace")
        procs.append((pid, (name + " " + arg).strip()))

    return procs


def reverseDict(d):
    """
    Return a dictionary with keys and values swapped:
    all values are lists to handle the different keys mapping to the same value
    """
    result = {}
    for a, v in d.iteritems():
        result.setdefault(v, []).append(a)
    return result


def chunk(lst, n):
    """
    Break lst into n-sized chunks
    """
    return [lst[i : i + n] for i in range(0, len(lst), n)]


# Collector Daemon Main entry point
#
if __name__ == "__main__":
    myPreferences = ZenProcessPreferences()

    myTaskFactory = SimpleTaskFactory(ZenProcessTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter, ConfigListener())
    daemon.run()
