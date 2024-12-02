##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2010, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""PingTask

Determines the availability of a IP addresses using ping (ICMP).

"""

import math
import logging

from zenoss.protocols.protobufs import zep_pb2 as events
from zope import component, interface

from Products.ZenCollector import interfaces
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenCollector.tasks import TaskStates, BaseTask
from Products.ZenEvents import ZenEventClasses
from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenUtils.IpUtil import ipunwrap
from Products.ZenUtils.Utils import unused

from .interfaces import IPingTask

COLLECTOR_NAME = "zenping"

STATUS_EVENT = {
    "eventClass": Status_Ping,
    "component": "zenping",
    "    eventGroup": "Ping",
}
SUPPRESSED = 2
_NAN = float("nan")

unused(DeviceProxy)

log = logging.getLogger("zen.zenping")


@interface.implementer(IPingTask)
class PingTask(BaseTask):

    STATE_PING_START = "PING_START"
    STATE_PING_STOP = "PING_STOP"
    STATE_STORE_PERF = "STORE_PERF_DATA"
    delayedIsUp = True

    def __init__(
        self, taskName, deviceId, scheduleIntervalSeconds, taskConfig
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
        super(PingTask, self).__init__(
            taskName, deviceId, scheduleIntervalSeconds, taskConfig
        )

        # Needed for interface
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = deviceId
        self._manageIp = ipunwrap(self._device.manageIp)
        self.interval = scheduleIntervalSeconds
        self._pingResult = None

        self._isUp = None
        self._daemon = component.queryUtility(interfaces.ICollector)
        self._dataService = component.queryUtility(interfaces.IDataService)
        self._eventService = component.queryUtility(interfaces.IEventService)
        self._preferences = component.queryUtility(
            interfaces.ICollectorPreferences, COLLECTOR_NAME
        )
        self._traceCache = self._preferences.options.traceCache
        if self._traceCache.get(self._devId, None) is None:
            self._traceCache[self._devId] = tuple()

        # Split up so that every interface's IP gets its own ping job
        self.config = self._device.monitoredIps[0]
        self._iface = self.config.iface
        self._lastErrorMsg = ""

        # by defautl don't pause after schedule
        self.pauseOnScheduled = False
        self._rtt = []

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to ping the device and any of its interfaces.
        @rtype: Twisted deferred object
        """
        raise NotImplementedError()

    def _getPauseOnScheduled(self):
        return self._pauseOnScheduled

    def _setPauseOnScheduled(self, value):
        self._pauseOnScheduled = value

    pauseOnScheduled = property(
        fget=_getPauseOnScheduled, fset=_setPauseOnScheduled
    )
    """Pause this task after it's been scheduled."""

    def scheduled(self, scheduler):
        """
        After the task has been scheduled, set the task in to the PAUSED state.

        @param scheduler: Collection Framework Scheduler
        @type scheduler: IScheduler
        """
        if self.pauseOnScheduled:
            scheduler.pauseTasksForConfig(self.configId)

    def _trace_get(self):
        return self._traceCache[self._devId]

    def _trace_set(self, value):
        self._traceCache[self._devId] = value

    trace = property(fget=_trace_get, fset=_trace_set)

    @property
    def isUp(self):
        """
        Determine if the device is up
        """
        return self._calculateState()

    def _calculateState(self):
        """
        Calculate if the device is up or down based on current ping statistics.
        Return None if unknown, False if down, and True if up.
        """

        # if there is not enough data to calulate return unknown
        if len(self._rtt) <= 0:
            return None

        lostPackets = len([rtt for rtt in self._rtt if math.isnan(rtt)])
        totalPackets = len(self._rtt)
        receivedPackets = totalPackets - lostPackets

        isUp = receivedPackets > 0
        return isUp

    def averageRtt(self):
        """
        Determine if the device ping times are lagging.
        @param timeout: in seconds
        @param minimalPercent: what percentage of ping RTTs ought to
               be less than the timeout. Between 0 and 1.
        Return None if can't compute, recent average RTT
            (in milliseconds) otherwise.
        """
        total = 0
        count = 0
        for rtt in self._rtt:
            if rtt is None or math.isnan(rtt):
                continue
            count += 1
            total += rtt
        if count == 0:
            return None
        return float(total) / count

    def resetPingResult(self):
        """
        Clear out current ping statistics.
        """
        self._rtt = []

    def logPingResult(self, pingResult):
        """
        Log the PingResult; set ping state, log to rrd.
        """
        if pingResult is None:
            raise ValueError("pingResult can not be None")
        self._rtt.append(pingResult.rtt)
        if pingResult.trace:
            self.trace = tuple(pingResult.trace)

    def sendPingEvent(self, msgTpl, severity, suppressed=False, **kwargs):
        """
        Send an event based on a ping job to the event backend.
        """
        msg = msgTpl % self._devId
        evt = dict(
            device=self._devId,
            ipAddress=self.config.ip,
            summary=msg,
            severity=severity,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup="Ping",
            component=self._iface,
        )

        if self._pingResult is not None:
            # explicitly set the event time based on the ping collection's time
            if self._pingResult.timestamp:
                evt["lastTime"] = evt["firstTime"] = self._pingResult.timestamp
            # include the last traceroute we know of this is not a Clear
            if severity and self._pingResult.trace:
                evt["lastTraceroute"] = str(self._pingResult.trace)

        if suppressed:
            evt["eventState"] = SUPPRESSED

        # mark this event with a flag if it applies to the managedIp component
        if self.config.ip == self._manageIp:
            evt["isManageIp"] = True

        # add extra details
        evt.update(kwargs)

        # send the event to the service
        self._eventService.sendEvent(evt)

        # ZEN-1584: if this proxy is for a component
        # that handles the manageIp, send a device level clear
        if (
            severity == events.SEVERITY_CLEAR
            and "isManageIp" in evt
            and evt["component"]
        ):
            evt["component"] = ""
            self._eventService.sendEvent(evt)

    def sendPingUp(self, msgTpl="%s is UP!"):
        """
        Send an ping up event to the event backend.
        """
        return self.sendPingEvent(msgTpl, events.SEVERITY_CLEAR)

    def sendPingDown(self, msgTpl="%s is DOWN!", **kwargs):
        """
        Send an ping down event to the event backend.
        """
        return self.sendPingEvent(msgTpl, events.SEVERITY_CRITICAL, **kwargs)

    def clearPingDegraded(self, rtt=None):
        """
        Send a "clear" ping degraded event to the event backend.
        """
        msgTpl = "%s is NOT LAGGING!"
        if rtt is not None:
            msgTpl += " (%.1f milliseconds)" % rtt
        return self.sendPingEvent(
            msgTpl,
            events.SEVERITY_CLEAR,
            eventClass=("%s/Lag" % Status_Ping),
            eventKey="ping_lag",
        )

    def sendPingDegraded(self, rtt=None):
        """
        Send a ping degraded event to the event backend.
        """
        msgTpl = "%s is LAGGING!"
        if rtt is not None:
            msgTpl += " (%.1f milliseconds)" % rtt
        return self.sendPingEvent(
            msgTpl,
            events.SEVERITY_WARNING,
            eventClass=("%s/Lag" % Status_Ping),
            eventKey="ping_lag",
        )

    def storeResults(self):
        """
        Store the datapoint results asked for by the RRD template.
        """
        if len(self._rtt) == 0:
            return

        # strip out NAN's
        rtts = [rtt for rtt in self._rtt if math.isnan(rtt) is False]
        if rtts:
            received = len(rtts)
            pingCount = len(self._rtt)
            minRtt = min(rtts)
            maxRtt = max(rtts)
            avgRtt = sum(rtts) / received
            varianceRtt = (
                sum([math.pow(rtt - avgRtt, 2) for rtt in rtts]) / received
            )
            stddevRtt = math.sqrt(varianceRtt)
            pingLoss = 100.0
            if pingCount > 0:
                pingLoss = (1 - (len(rtts) / pingCount)) * 100.0

            datapoints = {
                "rtt": avgRtt,
                "rtt_avg": avgRtt,
                "rtt_min": minRtt,
                "rtt_max": maxRtt,
                "rtt_losspct": pingLoss,
                "rtt_stddev": stddevRtt,
                "rcvCount": received,
            }
        else:
            pingLoss = 100
            datapoints = {
                "rtt_losspct": pingLoss,
            }

        for rrdMeta in self.config.points:
            id, metric, rrdType, rrdCommand, rrdMin, rrdMax, metadata = rrdMeta
            value = datapoints.get(id, None)
            if value is None:
                log.debug(
                    "No datapoint '%s' found on the %s pingTask", id, self
                )
            else:
                self._dataService.writeMetricWithMetadata(
                    metric,
                    value,
                    rrdType,
                    min=rrdMin,
                    max=rrdMax,
                    metadata=metadata,
                )
