#
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#

"""NmapPingTask

Pings a all devices in the current device list.
"""

import logging
import tempfile

from collections import defaultdict
from datetime import datetime, timedelta

from twisted.internet import defer, reactor, task as twistedTask
from zope import component, interface

from Products import ZenCollector
from Products.ZenCollector import interfaces
from Products.ZenCollector.tasks import BaseTask, TaskStates
from Products.ZenEvents import ZenEventClasses
from Products.ZenStatus import nmap, PingTask
from Products.ZenStatus.interfaces import IPingTaskFactory, IPingTaskCorrelator
from Products.ZenStatus.nmap.util import executeNmapCmd
from Products.ZenStatus.ping.CmdPingTask import CmdPingTask
from Products.ZenStatus.PingCollectionPreferences import (
    PingCollectionPreferences,
)

from .PingResult import PingResult

log = logging.getLogger("zen.NmapPingTask")

_CLEAR = 0
_CRITICAL = 5
_WARNING = 3

MAX_PARALLELISM = 150
DEFAULT_PARALLELISM = 10
MAX_NMAP_OVERHEAD = 0.5  # in seconds
MIN_PING_TIMEOUT = 0.1  # in seconds

# amount of IPs/events to process before giving time to the reactor
_SENDEVENT_YIELD_INTERVAL = 100  # should always be >= 1

# amount of time since last ping down before count is removed from dictionary
DOWN_COUNT_TIMEOUT_MINUTES = 15

# twisted.callLater has trouble with sys.maxint as call interval,
# just use a big interval, 100 years
_NEVER_INTERVAL = 60 * 60 * 24 * 365 * 100


class NmapPingCollectionPreferences(PingCollectionPreferences):
    def postStartup(self):
        """
        Hook in to application startup and start background NmapPingTask.
        """
        daemon = component.getUtility(interfaces.ICollector)
        task = NmapPingTask(
            "NmapPingTask", "NmapPingTask", taskConfig=daemon._prefs
        )
        # introduce a small delay to can have a chance to load some config
        task.startDelay = 5
        daemon._scheduler.addTask(task)
        if not daemon.options.disableCorrelator:
            correlationBackend = daemon.options.correlationBackend
            task._correlate = component.getUtility(
                IPingTaskCorrelator, correlationBackend
            )
        task.disable_correlator = daemon.options.disableCorrelator

    def buildOptions(self, parser):
        super(NmapPingCollectionPreferences, self).buildOptions(parser)
        parser.add_option(
            "--connected-ip-suppress",
            dest="connectedIps",
            default=False,
            action="store_true",
            help="Suppress ping downs using interfaces on a device whose "
            "IPs may not be monitored",
        )

    def runPostConfigTasks(self):
        daemon = component.getUtility(interfaces.ICollector)
        daemon._scheduler.resetStats("NmapPingTask")


class NPingTaskFactory(object):

    """
    A Factory to create PingTasks that do not run. This allows NmapPingTask
    to use the created PingTasks as placeholders for configuration.
    """

    interface.implements(IPingTaskFactory)

    def __init__(self):
        self.reset()

    def build(self):
        # Task spliter will gurantee every task has exactly one monitoredIp
        if self.config.monitoredIps[0].ipVersion == 6:
            # nmap does not support IPV6 ping/traceroute, use CmdPing
            log.debug(
                "Creating an IPv6 task: %s", self.config.monitoredIps[0].ip
            )
            task = CmdPingTask(
                self.name,
                self.configId,
                self.interval,
                self.config,
            )
        else:
            log.debug(
                "Creating an IPv4 task: %s", self.config.monitoredIps[0].ip
            )
            task = PingTask(
                self.name,
                self.configId,
                self.interval,
                self.config,
            )
            # don't run the tasks, they are used for storing config
            task.pauseOnScheduled = True
            task.interval = _NEVER_INTERVAL
        return task

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None


class NmapPingTask(BaseTask):
    interface.implements(ZenCollector.interfaces.IScheduledTask)
    """
    NmapPingTask pings all PingTasks using using nmap.
    """

    def __init__(
        self, taskName, configId, scheduleIntervalSeconds=60, taskConfig=None
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
        super(NmapPingTask, self).__init__(
            taskName, configId, scheduleIntervalSeconds, taskConfig=None
        )

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._preferences = taskConfig

        self._daemon = component.getUtility(ZenCollector.interfaces.ICollector)
        self._dataService = component.queryUtility(
            ZenCollector.interfaces.IDataService
        )
        self._eventService = component.queryUtility(
            ZenCollector.interfaces.IEventService
        )

        self._pings = 0
        self._nmapPresent = False  # assume nmap is not present at startup
        self._nmapIsSuid = False  # assume nmap is not SUID at startup
        self._cycleIntervalReasonable = (
            True  # assume interval is fine at startup
        )
        self.collectorName = self._daemon._prefs.collectorName

        # maps task name to ping down count and time of last ping down
        self._down_counts = defaultdict(lambda: (0, None))

    def _detectCycleInterval(self):
        """
        Detect whether the Ping Cycle Time is too short.
        """
        cycleInterval = self._daemon._prefs.pingCycleInterval
        minCycleInterval = MIN_PING_TIMEOUT + MAX_NMAP_OVERHEAD
        newValue = cycleInterval >= minCycleInterval
        if self._cycleIntervalReasonable != newValue:
            self._cycleIntervalReasonable = newValue
            if self._cycleIntervalReasonable is False:
                raise nmap.ShortCycleIntervalError(cycleInterval)
        self._sendShortCycleInterval(cycleInterval)

    def _sendShortCycleInterval(self, cycleInterval):
        """
        Send/Clear event to show that ping cycle time is short/fine.
        """
        if self._cycleIntervalReasonable:
            msg = "ping cycle time (%.1f seconds) is fine" % cycleInterval
            severity = _CLEAR
        else:
            minimum = MIN_PING_TIMEOUT + MAX_NMAP_OVERHEAD
            msg = (
                "ping cycle time (%.1f seconds) is too short "
                "(keep it under %.1f seconds)" % (cycleInterval, minimum)
            )
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup="Ping",
            eventKey="cycle_interval",
            severity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    def _correlationExecution(self, ex=None):
        """
        Send/Clear event to show that correlation is executed properly.
        """
        if ex is None:
            msg = "correlation executed correctly"
            severity = _CLEAR
        else:
            msg = "correlation did not execute correctly: %s" % ex
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup="Ping",
            eventKey="correlation_execution",
            severity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    def _nmapExecution(self, ex=None):
        """
        Send/Clear event to show that nmap is executed properly.
        """
        if ex is None:
            msg = "nmap executed correctly"
            severity = _CLEAR
        else:
            msg = "nmap did not execute correctly: %s" % ex
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup="Ping",
            eventKey="nmap_execution",
            severity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    @defer.inlineCallbacks
    def doTask(self):
        """
        BatchPingDevices !
        """
        log.debug("---- BatchPingDevices ----")

        if self.interval != self._daemon._prefs.pingCycleInterval:
            log.info(
                "Changing ping interval from %r to %r ",
                self.interval,
                self._daemon._prefs.pingCycleInterval,
            )
            self.interval = self._daemon._prefs.pingCycleInterval

        try:
            yield self._batchPing()  # will clear nmap_execution

        except nmap.ShortCycleIntervalError:
            self._sendShortCycleInterval(self.interval)
        except nmap.NmapExecutionError as ex:
            self._nmapExecution(ex)

    def _getPingTasks(self):
        """
        Iterate the daemons task list and find PingTask tasks that are IPV4.
        """
        tasks = self._daemon._scheduler._tasks
        pingTasks = {}
        for configName, task in tasks.iteritems():
            if isinstance(task.task, PingTask):
                if task.task.config.ipVersion == 4:
                    pingTasks[configName] = task.task
        return pingTasks

    @defer.inlineCallbacks
    def _batchPing(self):
        """
        Find the IPs, ping/traceroute, parse, correlate, and send events.
        """
        # find all devices to Ping
        ipTasks = self._getPingTasks()
        if len(ipTasks) == 0:
            log.debug("No ips to ping!")
            raise StopIteration()  # exit this generator

        # Make sure the cycle interval is not unreasonably short.
        self._detectCycleInterval()

        # only increment if we have tasks to ping
        self._pings += 1
        with tempfile.NamedTemporaryFile(prefix="zenping_nmap_") as tfile:
            ips = []
            for taskName, ipTask in ipTasks.iteritems():
                ips.append(ipTask.config.ip)
                ipTask.resetPingResult()  # clear out previous run's results
            ips.sort()
            for ip in ips:
                tfile.write("%s\n" % ip)
            tfile.flush()

            # ping up to self._preferences.pingTries
            tracerouteInterval = self._daemon.options.tracerouteInterval

            # determine if traceroute needs to run
            doTraceroute = False
            if tracerouteInterval > 0:
                if self._pings == 0 or (self._pings % tracerouteInterval) == 0:
                    doTraceroute = True  # try to traceroute on next ping

            import time

            i = 0
            for attempt in range(0, self._daemon._prefs.pingTries):

                start = time.time()
                results = yield executeNmapCmd(
                    tfile.name,
                    traceroute=doTraceroute,
                    num_devices=len(ipTasks),
                    dataLength=self._daemon.options.dataLength,
                    pingTries=self._daemon._prefs.pingTries,
                    pingTimeOut=self._preferences.pingTimeOut,
                    pingCycleInterval=self._daemon._prefs.pingCycleInterval,
                )
                elapsed = time.time() - start
                log.debug("Nmap execution took %f seconds", elapsed)

                # only do traceroute on the first ping attempt, if at all
                doTraceroute = False

                # record the results!
                for taskName, ipTask in ipTasks.iteritems():
                    i += 1
                    ip = ipTask.config.ip
                    if ip in results:
                        result = results[ip]
                        ipTask.logPingResult(result)
                    else:
                        # received no result, log as down
                        ipTask.logPingResult(PingResult(ip, isUp=False))
                    # give time to reactor to send events if necessary
                    if i % _SENDEVENT_YIELD_INTERVAL:
                        yield twistedTask.deferLater(reactor, 0, lambda: None)

            self._cleanupDownCounts()
            dcs = self._down_counts
            delayCount = self._daemon.options.delayCount
            pingTimeOut = self._preferences.pingTimeOut
            for taskName, ipTask in ipTasks.iteritems():
                i += 1
                if ipTask.isUp:
                    if taskName in dcs:
                        del dcs[taskName]
                    log.debug("%s is up!", ipTask.config.ip)
                    ipTask.delayedIsUp = True
                    ipTask.sendPingUp()
                    averageRtt = ipTask.averageRtt()
                    if averageRtt is not None:
                        if (
                            averageRtt / 1000.0 > pingTimeOut
                        ):  # millisecs to secs
                            ipTask.sendPingDegraded(rtt=averageRtt)
                        else:
                            ipTask.clearPingDegraded(rtt=averageRtt)
                else:
                    dcs[taskName] = (dcs[taskName][0] + 1, datetime.now())
                    if dcs[taskName][0] > delayCount:
                        log.debug(
                            "%s is down, %r", ipTask.config.ip, ipTask.trace
                        )
                        ipTask.delayedIsUp = False
                    else:
                        log.debug(
                            "%s is down. %s ping downs received. "
                            "Delaying events until more than %s ping "
                            "downs are received.",
                            ipTask.config.ip,
                            dcs[taskName][0],
                            delayCount,
                        )

                ipTask.storeResults()
                # give time to reactor to send events if necessary
                if i % _SENDEVENT_YIELD_INTERVAL:
                    yield twistedTask.deferLater(reactor, 0, lambda: None)

            if not self.disable_correlator:
                try:
                    yield defer.maybeDeferred(self._correlate, ipTasks)
                except Exception as ex:
                    self._correlationExecution(ex)
                    log.critical(
                        "There was a problem performing correlation: %s", ex
                    )
                else:
                    self._correlationExecution()  # send clear
            else:
                downTasks = (
                    ipTask
                    for ipTask in ipTasks.values()
                    if not (ipTask.isUp or ipTask.delayedIsUp)
                )
                for ipTask in downTasks:
                    ipTask.sendPingDown()

            self._nmapExecution()

    def _cleanupDownCounts(self):
        """Clear out old down counts so process memory utilization doesn't
        grow."""
        now = datetime.now()
        timeout = timedelta(minutes=DOWN_COUNT_TIMEOUT_MINUTES)
        for taskName, (down_count, last_time) in self._down_counts.iteritems():
            if now - last_time > timeout:
                del self._down_counts[taskName]

    def _correlate(self, ipTasks):
        raise Exception("_correlate is not implemented in %r", self.__class__)

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        return ""
