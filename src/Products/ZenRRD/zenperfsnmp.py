#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2010, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zenperfsnmp

Gets SNMP performance data and stores it in RRD files.

"""

import logging

from collections import deque
from datetime import datetime, timedelta

import zope.interface

from pynetsnmp import oids
from pynetsnmp.netsnmp import SnmpTimeoutError, NetSnmpError
from pynetsnmp.twistedsnmp import snmpprotocol
from pynetsnmp.errors import SnmpUsmError, SnmpUsmStatsError
from twisted.internet import defer, error

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import (
    ICollectorPreferences,
    IDataService,
    IEventService,
    IScheduledTask,
)
from Products.ZenCollector.tasks import (
    BaseTask,
    SimpleTaskFactory,
    SimpleTaskSplitter,
    TaskStates,
)
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. SnmpDeviceProxy.
from Products.ZenUtils.Utils import unused
from Products.ZenHub.services.SnmpPerformanceConfig import SnmpDeviceProxy
from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo

unused(SnmpDeviceProxy, SnmpConnInfo)

log = logging.getLogger("zen.zenperfsnmp")

COLLECTOR_NAME = "zenperfsnmp"
MAX_BACK_OFF_MINUTES = 20


@zope.interface.implementer(ICollectorPreferences)
class SnmpPerformanceCollectionPreferences(object):
    def __init__(self):
        """
        Constructs a new SnmpPerformanceCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.configCycleInterval = 20  # minutes
        self.cycleInterval = 5 * 60  # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = (
            "Products.ZenHub.services.SnmpPerformanceConfig"
        )

        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        parser.add_option(
            "--showrawresults",
            dest="showrawresults",
            action="store_true",
            default=False,
            help="Show the raw RRD values. For debugging purposes only.",
        )

        parser.add_option(
            "--maxbackoffminutes",
            dest="maxbackoffminutes",
            default=MAX_BACK_OFF_MINUTES,
            type="int",
            help="Deprecated since 4.1.1. No longer used",
        )

        parser.add_option(
            "--triespercycle",
            dest="triesPerCycle",
            default=2,
            type="int",
            help="How many attempts per cycle should be made to get data "
            "for an OID from a non-responsive device. Minimum of 2",
        )

        parser.add_option(
            "--maxtimeouts",
            dest="maxTimeouts",
            default=3,
            type="int",
            help="How many consecutive time outs per cycle before "
            "stopping attempts to collect",
        )

        parser.add_option(
            "--oid",
            dest="oid",
            type="string",
            default=None,
            help="Collect just for one oid (datasource)",
        )

    def postStartup(self):
        pass


class CycleExceeded(Exception):
    pass


class StopTask(Exception):
    pass


STATUS_EVENT = {"eventClass": Status_Snmp, "eventGroup": "SnmpTest"}

_usm_stat_message = {
    oids.WrongDigest: (
        "invalid zSnmpAuthPassphrase/zSnmpAuthProtocol properties"
    ),
    oids.DecryptionError: (
        "invalid zSnmpPrivPassphrase/zSnmpPrivProtocol properties"
    ),
    oids.UnknownUserName: "invalid zSnmpSecurityName property",
    oids.UnknownSecurityLevel: "invalid zSnmp* properties",
}


@zope.interface.implementer(IScheduledTask)
class SnmpPerformanceCollectionTask(BaseTask):
    """
    A task that performs periodic performance collection for devices providing
    data via SNMP agents.
    """

    STATE_CONNECTING = "CONNECTING"
    STATE_FETCH_PERF = "FETCH_PERF_DATA"
    STATE_STORE_PERF = "STORE_PERF_DATA"

    def __init__(
        self, deviceId, taskName, scheduleIntervalSeconds, taskConfig
    ):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(SnmpPerformanceCollectionTask, self).__init__(
            deviceId, taskName, taskConfig.cycleInterval, taskConfig
        )

        # Needed for interface
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = self._device.id
        self._manageIp = self._device.snmpConnInfo.manageIp
        self._maxOidsPerRequest = self._device.zMaxOIDPerRequest
        log.debug(
            "SnmpPerformanceCollectionTask.__init__: "
            "self._maxOidsPerRequest=%s",
            self._maxOidsPerRequest,
        )
        self.interval = self._device.cycleInterval
        self._collectedOids = set()

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        self._preferences = zope.component.queryUtility(
            ICollectorPreferences, COLLECTOR_NAME
        )

        self._snmpProxy = None
        self._snmpConnInfo = self._device.snmpConnInfo
        log.info("SNMP info summary  %s", self._snmpConnInfo.summary())
        self._oids = self._device.oids
        self._oidDeque = deque(self._oids.keys())
        self._good_oids = set()
        # oids not returning data
        self._bad_oids = set()
        self._snmpPort = snmpprotocol.port()
        self.triesPerCycle = max(2, self._preferences.options.triesPerCycle)
        self._maxTimeouts = self._preferences.options.maxTimeouts
        self._chosenOid = self._preferences.options.oid

        self._lastErrorMsg = ""
        self._cycleExceededCount = 0
        self._stoppedTaskCount = 0
        self._snmpV3ErrorCount = 0

        # whether or not we got a response during a collection interval
        self._responseReceived = False

    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        msg = reason.getErrorMessage()
        if not msg:  # Sometimes we get blank error messages
            msg = reason.__class__
        msg = "%s %s" % (self._devId, msg)

        # Leave 'reason' alone to generate a traceback

        if self._lastErrorMsg != msg:
            self._lastErrorMsg = msg
            if msg:
                log.error(msg)

        return reason

    def _connectCallback(self, result):
        """
        Callback called after a successful connect to the remote device.
        """
        # If we want to model things first before doing collection,
        # that code goes here.
        log.debug(
            "Connected to %s [%s] using SNMP %s",
            self._devId,
            self._manageIp,
            self._snmpConnInfo.zSnmpVer,
        )
        self._collectedOids.clear()
        return result

    def _checkTaskTime(self):
        elapsed = datetime.now() - self._doTask_start

        if elapsed >= timedelta(seconds=self._device.cycleInterval):
            raise CycleExceeded(
                "Elapsed time %s seconds greater than %s seconds"
                % (elapsed.total_seconds(), self._device.cycleInterval)
            )
        # Check to to see if we are about to run out of time,
        # if so stop task.
        if elapsed >= timedelta(seconds=self._device.cycleInterval * 0.99):
            raise StopTask("Elapsed time %s sec" % elapsed.total_seconds())

    def getOidsSet(self):
        if self._chosenOid:
            return {oid for oid in self._oids if self._chosenOid in oid}
        else:
            return set(self._oids)

    def _untestedOids(self):
        return self.getOidsSet() - self._bad_oids - self._good_oids

    def _uncollectedOids(self):
        return self.getOidsSet() - self._bad_oids - self._collectedOids

    @defer.inlineCallbacks
    def _fetchPerf(self):
        """
        Get performance data for all the monitored components on a device
        """
        log.debug("Retrieving OIDs from %s [%s]", self._devId, self._manageIp)
        if not self._oids:
            defer.returnValue(None)

        # Do known untested and good oids in chunks.
        # First run all oids will be unkown since they aren't in the good
        # oid list or the bad oid list.
        oids_to_test = list(self._untestedOids())
        oids_to_test.extend(self._good_oids)
        log.debug(
            "%s [%s] collecting %s oids out of %s",
            self._devId,
            self._manageIp,
            len(oids_to_test),
            len(self._oids),
        )
        chunk_size = self._maxOidsPerRequest
        maxTries = self.triesPerCycle
        try_count = 0
        consecutiveTimeouts = 0
        while oids_to_test and try_count < maxTries:
            try_count += 1
            if try_count > 1:
                log.debug(
                    "%s [%s] some oids still uncollected after %s tries, "
                    "trying again with chunk size %s",
                    self._devId,
                    self._manageIp,
                    try_count - 1,
                    chunk_size,
                )
            oid_chunks = self.chunk(oids_to_test, chunk_size)
            for oid_chunk in oid_chunks:
                try:
                    self._checkTaskTime()
                    log.debug(
                        "Fetching OID chunk size %s from %s [%s] - %s",
                        chunk_size,
                        self._devId,
                        self._manageIp,
                        oid_chunk,
                    )
                    yield self._fetchPerfChunk(oid_chunk)
                    consecutiveTimeouts = 0
                    log.debug(
                        "Finished fetchPerfChunk call %s [%s]",
                        self._devId,
                        self._manageIp,
                    )
                except error.TimeoutError:
                    log.debug(
                        "timeout for %s [%s] oids - %s",
                        self._devId,
                        self._manageIp,
                        oid_chunk,
                    )
                    consecutiveTimeouts += 1
                    if consecutiveTimeouts >= self._maxTimeouts:
                        log.debug(
                            "%s consecutive timeouts, "
                            "abandoning run for %s [%s]",
                            consecutiveTimeouts,
                            self._devId,
                            self._manageIp,
                        )
                        raise
                except SnmpTimeoutError:
                    # Only seem to get these for V3 and subsequent calls
                    # throw credential exceptions, so just bail here.
                    log.debug(
                        "SnmpTimeoutError for %s [%s] oids - %s",
                        self._devId,
                        self._manageIp,
                        oid_chunk,
                    )
                    raise
            # Can still have untested oids from a chunk that failed to return
            # data, one or more of those may be bad.  Run with a smaller
            # chunk size to identify bad oid. Can also have uncollected good
            # oids because of timeouts.
            oids_to_test = list(self._uncollectedOids())
            chunk_size = 1

    @defer.inlineCallbacks
    def _fetchPerfChunk(self, oid_chunk):
        self.state = SnmpPerformanceCollectionTask.STATE_FETCH_PERF
        update_x = {}
        try:
            update_x = yield self._snmpProxy.get(
                oid_chunk,
                self._snmpConnInfo.zSnmpTimeout,
                self._snmpConnInfo.zSnmpTries,
            )
        except (error.TimeoutError, SnmpTimeoutError, SnmpUsmStatsError):
            raise
        except Exception as e:
            log.exception(
                "Failed to collect on %s (%s: %s)",
                self.configId,
                e.__class__.__name__,
                e,
            )
            # Something happened, not sure what.
            raise
        finally:
            self.state = TaskStates.STATE_RUNNING
        update = {}

        # We got a response
        self._responseReceived = True
        # Remove leading and trailing dots
        for oid, value in dict(update_x).items():
            update[oid.strip(".")] = value

        if not update:
            # Empty update is probably a bad OID in the request somewhere,
            # remove them from good oids. These will run in single mode so
            # we can figure out which ones are good or bad.
            if len(oid_chunk) == 1:
                self._mark_bad_oids(oid_chunk)
            else:
                log.warning(
                    "No results returned, will run in separately to "
                    "determine which oids are valid  device=%s oids=%s",
                    self.configId,
                    oid_chunk,
                )
                self._remove_from_good_oids(oid_chunk)
        else:
            for oid in oid_chunk:
                if oid not in update:
                    self._mark_bad_oids([oid])
            self.state = SnmpPerformanceCollectionTask.STATE_STORE_PERF
            try:
                for oid, value in update.items():
                    if oid not in self._oids:
                        log.error(
                            "SNMP get returned unexpected OID: %s %s",
                            self.configId,
                            oid,
                        )
                        continue

                    # We should always get something useful back
                    if value == "" or value is None:
                        if oid not in self._bad_oids:
                            self._mark_bad_oids([oid])
                        continue

                    self._good_oids.add(oid)
                    self._bad_oids.discard(oid)
                    self._collectedOids.add(oid)
                    # An OID's data can be stored multiple times
                    for rrdMeta in self._oids[oid]:
                        (
                            contextId,
                            metric,
                            rrdType,
                            rrdCommand,
                            rrdMin,
                            rrdMax,
                            metadata,
                        ) = rrdMeta
                        path = metadata.get("contextKey")
                        if self._chosenOid:
                            log.info(
                                "OID: %s >> Component: %s >> "
                                "DataPoint: %s %s",
                                oid,
                                path,
                                metric,
                                value,
                            )
                        try:
                            # See SnmpPerformanceConfig line
                            # _getComponentConfig.
                            yield self._dataService.writeMetricWithMetadata(
                                metric,
                                value,
                                rrdType,
                                min=rrdMin,
                                max=rrdMax,
                                metadata=metadata,
                            )
                        except Exception as e:
                            log.exception(
                                "Failed to write to metric service: %s %s %s",
                                path,
                                e.__class__.__name__,
                                e,
                            )
                            continue
            finally:
                self.state = TaskStates.STATE_RUNNING

    @defer.inlineCallbacks
    def _processBadOids(self, previous_bad_oids):
        if previous_bad_oids:
            log.debug(
                "%s Re-checking %s bad oids", self.name, len(previous_bad_oids)
            )
            oids_to_test = set(previous_bad_oids)
            num_checked = 0
            max_bad_check = max(10, self._maxOidsPerRequest)
            while num_checked < max_bad_check and oids_to_test:
                self._checkTaskTime()
                # Using deque as a rotating list so that next time we
                # start where we left off.
                oid = self._oidDeque[0]  # get the first one
                self._oidDeque.rotate(1)  # move it to the end
                if oid in oids_to_test:  # fetch if we care
                    oids_to_test.remove(oid)
                    num_checked += 1
                    try:
                        yield self._fetchPerfChunk([oid])
                    except (error.TimeoutError, SnmpTimeoutError):
                        log.debug(
                            "%s timed out re-checking bad oid %s",
                            self.name,
                            oid,
                        )

    def _sendStatusEvent(
        self, summary, eventKey=None, severity=Event.Error, details=None
    ):
        if details is None:
            details = {}
        event = details.copy()
        event.update(STATUS_EVENT)
        self._eventService.sendEvent(
            event,
            severity=severity,
            device=self.configId,
            eventKey=eventKey,
            summary=summary,
        )

    @defer.inlineCallbacks
    def _doCollectOids(self, ignored):
        previous_bad_oids = list(self._bad_oids)
        taskStopped = False

        try:
            try:
                yield self._fetchPerf()
                # we have time; try to collect previous bad oids:
                yield self._processBadOids(previous_bad_oids)
            except StopTask as e:
                taskStopped = True
                self._stoppedTaskCount += 1
                log.warning(
                    "Device %s [%s] Task stopped collecting to avoid "
                    "exceeding cycle interval - %s",
                    self._devId,
                    self._manageIp,
                    e,
                )
                self._logOidsNotCollected(
                    "Task was stopped so as not exceed cycle interval"
                )
            except (error.TimeoutError, SnmpTimeoutError):
                log.debug(
                    "Device %s [%s] snmp timed out ",
                    self._devId,
                    self._manageIp,
                )
            except SnmpUsmStatsError as ex:
                message = _usm_stat_message.get(ex.oid)
                if not message:
                    # The UnknownSecurityLevel message also works as a
                    # generic USM stats error message.
                    message = _usm_stat_message.get(oids.UnknownSecurityLevel)
                log.error("%s  device=%s", message, self._devId)
                raise

            if self._snmpConnInfo.zSnmpVer == "v3":
                self._sendStatusEvent(
                    "SNMP v3 error cleared",
                    eventKey="snmp_v3_error",
                    severity=Event.Clear,
                )

            # send snmp error clear
            self._sendStatusEvent(
                "SNMP error cleared",
                eventKey="snmp_error",
                severity=Event.Clear,
            )

            # clear cycle exceeded event
            self._sendStatusEvent(
                "Collection run time restored below interval",
                eventKey="interval_exceeded",
                severity=Event.Clear,
            )

            if self._responseReceived:
                # clear down event
                self._sendStatusEvent(
                    "SNMP agent up",
                    eventKey="agent_down",
                    severity=Event.Clear,
                )
                if not self._collectedOids:
                    # send event if no oids collected - all oids seem to be bad
                    oidSample = self._oids.keys()[: self._maxOidsPerRequest]
                    oidDetails = {
                        "oids_configured": "%s oids configured for device"
                        % len(self._oids),
                        "oid_sample": "Subset of oids requested %s"
                        % oidSample,
                    }
                    self._sendStatusEvent(
                        "No values returned for configured oids",
                        eventKey="no_oid_results",
                        details=oidDetails,
                    )
                else:
                    self._sendStatusEvent(
                        "oids collected",
                        eventKey="no_oid_results",
                        severity=Event.Clear,
                    )
                    if len(self._collectedOids) == len(
                        set(self._oids) - self._bad_oids
                    ):
                        # this should clear failed to collect some oids event
                        self._sendStatusEvent(
                            "Gathered all OIDs",
                            eventKey="partial_oids_collected",
                            severity=Event.Clear,
                        )
                    else:
                        summary = "Failed to collect some OIDs"
                        if taskStopped:
                            summary = (
                                "%s - was not able to collect all oids "
                                "within collection interval"
                            ) % summary
                        self._sendStatusEvent(
                            summary,
                            eventKey="partial_oids_collected",
                            severity=Event.Warning,
                        )
            else:
                # Send event if no response received
                # - all timeouts or other errors
                self._sendStatusEvent(
                    "SNMP agent down - no response received",
                    eventKey="agent_down",
                )
        except CycleExceeded as e:
            self._cycleExceededCount += 1
            log.warning(
                "Device %s [%s] scan stopped because time exceeded "
                "cycle interval, %s",
                self._devId,
                self._manageIp,
                e,
            )
            self._logOidsNotCollected("cycle exceeded")
            self._sendStatusEvent(
                "Scan stopped; Collection time exceeded interval - %s" % e,
                eventKey="interval_exceeded",
            )
        except SnmpUsmError as e:
            self._logOidsNotCollected("of %s" % (e,))
            self._snmpV3ErrorCount += 1
            log.error(
                "cannot connect to SNMP agent  device=%s error=%s",
                self.configId,
                e,
            )
            self._sendStatusEvent(
                "Cannot connect to SNMP agent on {0._devId}: {1}".format(
                    self, e
                ),
                eventKey="snmp_v3_error",
            )
        except NetSnmpError as e:
            self._logOidsNotCollected("of %s" % (e,))
            log.error(
                "cannot connect to SNMP agent  device=%s error=%s",
                self.configId,
                e,
            )
            self._sendStatusEvent(
                "Cannot connect to SNMP agent on {0._devId}: {1}".format(
                    self, e
                ),
                eventKey="snmp_error",
            )
        finally:
            self._logTaskOidInfo(previous_bad_oids)

    def _remove_from_good_oids(self, oids):
        self._good_oids.difference_update(oids)

    def _mark_bad_oids(self, oids):
        """
        Report any bad OIDs and then track the OID so we
        don't generate any further errors.
        """
        # make sure oids aren't in good set
        self._remove_from_good_oids(oids)
        for oid in oids:
            if oid in self._bad_oids or oid not in self._oids:
                continue
            self._bad_oids.add(oid)
            names = [dp[0] for dp in self._oids[oid]]
            log.warning(
                "no result for oid  device=%s oid=%s names=%s",
                self._devId,
                oid,
                names,
            )

    def _finished(self, result):
        """
        Callback activated when the task is complete

        @parameter result: results of SNMP gets
        @type result: array of (boolean, dictionaries)
        """

        try:
            self._close()
        except Exception as ex:
            log.warning("Failed to close device %s: error %s", self._devId, ex)

        doTask_end = datetime.now()
        duration = doTask_end - self._doTask_start
        if duration > timedelta(seconds=self._device.cycleInterval):
            log.warning(
                "Collection for %s took %s seconds; "
                "cycle interval is %s seconds.",
                self.configId,
                duration.total_seconds(),
                self._device.cycleInterval,
            )
        else:
            log.debug(
                "Collection time for %s was %s seconds; "
                "cycle interval is %s seconds.",
                self.configId,
                duration.total_seconds(),
                self._device.cycleInterval,
            )

        # Return the result so the framework can track success/failure
        return result

    def cleanup(self):
        return self._close()

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to scan the OIDs on a device.
        @rtype: Twisted deferred object
        """
        self._doTask_start = datetime.now()
        self._responseReceived = False
        # See if we need to connect first before doing any collection
        if self._scheduler.cyberark:
            d = defer.maybeDeferred(
                self._scheduler.cyberark.update_config,
                self._devId,
                self._snmpConnInfo,
            )
            d.addCallback(self._connect)
        else:
            d = defer.maybeDeferred(self._connect)
        d.addCallbacks(self._connectCallback, self._failure)
        d.addCallback(self._doCollectOids)
        # Call _finished for both success and error scenarois
        d.addBoth(self._finished)

        # Wait until the Deferred actually completes
        return d

    def _logTaskOidInfo(self, previous_bad_oids):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                "Device %s [%s] %d of %d OIDs scanned successfully",
                self._devId,
                self._manageIp,
                len(self._collectedOids),
                len(self._oids),
            )
            untested_oids = self._untestedOids()
            log.debug(
                "Device %s [%s] has %d good oids, "
                "%d bad oids and %d untested oids out of %d configured",
                self._devId,
                self._manageIp,
                len(self._good_oids),
                len(self._bad_oids),
                len(untested_oids),
                len(self._oids),
            )

        newBadOids = self._bad_oids - set(previous_bad_oids)
        if newBadOids:
            log.info(
                "%s: Detected %s bad oids this cycle",
                self.name,
                len(newBadOids),
            )
            log.debug("%s: Bad oids detected - %s", self.name, newBadOids)

    def _logOidsNotCollected(self, reason):
        oidsNotCollected = self._uncollectedOids()
        if oidsNotCollected:
            log.debug(
                "%s Oids not collected because %s - %s",
                self.name,
                reason,
                oidsNotCollected,
            )

    def _connect(self, ignored=None):
        """
        Create a connection to the remote device
        """
        self.state = SnmpPerformanceCollectionTask.STATE_CONNECTING
        if (
            self._snmpProxy is None
            or self._snmpProxy._snmpConnInfo != self._snmpConnInfo
        ):
            try:
                self._snmpProxy = self._snmpConnInfo.createSession(
                    protocol=self._snmpPort.protocol
                )
                self._snmpProxy.open()
                self._sendStatusEvent(
                    "SNMP config error cleared",
                    eventKey="snmp_config_error",
                    severity=Event.Clear,
                )
            except Exception as ex:
                self._close()
                log.error("failed to create SNMP session: %s", ex)
                self._sendStatusEvent(
                    "SNMP config error: {}".format(ex),
                    eventKey="snmp_config_error",
                )
                raise
        return self._snmpProxy

    def _close(self):
        """
        Close down the connection to the remote device
        """
        if self._snmpProxy:
            try:
                self._snmpProxy.close()
            finally:
                self._snmpProxy = None

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = "%s using SNMP %s\n" % (
            self.name,
            self._snmpConnInfo.zSnmpVer,
        )
        display += (
            "%s Cycles Exceeded: %s; "
            "V3 Error Count: %s; "
            "Stopped Task Count: %s\n"
        ) % (
            self.name,
            self._cycleExceededCount,
            self._snmpV3ErrorCount,
            self._stoppedTaskCount,
        )
        display += "%s OIDs configured: %d \n" % (
            self.name,
            len(self._oids.keys()),
        )
        display += "%s Good OIDs: %d - %s\n" % (
            self.name,
            len(self._good_oids),
            self._good_oids,
        )
        display += "%s Bad OIDs: %d - %s\n" % (
            self.name,
            len(self._bad_oids),
            self._bad_oids,
        )

        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


if __name__ == "__main__":
    myPreferences = SnmpPerformanceCollectionPreferences()
    myTaskFactory = SimpleTaskFactory(SnmpPerformanceCollectionTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
