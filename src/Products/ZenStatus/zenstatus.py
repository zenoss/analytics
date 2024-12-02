#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zenstatus

Check the TCP/IP connectivity of IP services.
UDP is specifically not supported.
"""

import logging

from twisted.internet import defer

import zope.component
import zope.interface

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import (
    ICollectorPreferences,
    IEventService,
    IScheduledTask,
)
from Products.ZenCollector.tasks import (
    BaseTask,
    SimpleTaskFactory,
    SubConfigurationTaskSplitter,
    TaskStates,
)
from Products.ZenStatus.ZenTcpClient import ZenTcpClient
from Products.ZenUtils.Utils import unused


# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. DeviceProxy.
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.ZenStatusConfig import ServiceProxy

unused(ServiceProxy)
unused(DeviceProxy)

log = logging.getLogger("zen.zenstatus")


class ServiceTaskSplitter(SubConfigurationTaskSplitter):
    subconfigName = "components"

    def makeConfigKey(self, config, subconfig):
        return (config.id, config.configCycleInterval, subconfig.component)


# Create an implementation of the ICollectorPreferences interface so that the
# ZenCollector framework can configure itself from our preferences.
@zope.interface.implementer(ICollectorPreferences)
class ZenStatusPreferences(object):
    def __init__(self):
        """
        Construct a new ZenStatusPreferences instance and provide default
        values for needed attributes.
        """
        self.collectorName = "zenstatus"
        self.cycleInterval = 60  # seconds
        self.configCycleInterval = 20  # minutes
        self.statusCycleInterval = 60
        self.options = None

        # the configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = "Products.ZenHub.services.ZenStatusConfig"

    def buildOptions(self, parser):
        """
        add any zenstatus specific command line options here
        """
        pass

    def postStartup(self):
        """
        process any zenstatus specific command line options here
        """
        pass


@zope.interface.implementer(IScheduledTask)
class ZenStatusTask(BaseTask):
    def __init__(self, name, configId, scheduleIntervalSeconds, taskConfig):
        """
        Construct a new task for checking the status

        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(ZenStatusTask, self).__init__(
            name, configId, scheduleIntervalSeconds, taskConfig
        )

        self.name = name
        self.configId = configId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE
        self.log = log
        self.cfg = taskConfig.components[0]
        self._devId = self.cfg.device
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = zope.component.queryUtility(
            ICollectorPreferences, "zenstatus"
        )

    def _scan_device(self, ip_address):
        log.debug(
            "Scanning device %s (%s) port %s",
            self._devId,
            ip_address,
            self.cfg.port,
        )
        job = ZenTcpClient(self.cfg, self.cfg.status)
        return job.start(ip_address)

    def doTask(self):
        d = self._scan_device(self.cfg.ip)
        if self.cfg.ip != self.cfg.deviceManageIp:
            d.addCallbacks(self.processTestWithRetry, self.handleExceptions)
        else:
            d.addCallback(self.processTest)
            d.addErrback(self.handleExceptions)
        return d

    def processTestWithRetry(self, result):
        """
        Test a connection to a device.

        @parameter result: device and TCP service to test
        @type result: ZenTcpClient object
        """
        evt = result.getEvent()
        if evt:
            if evt["severity"] != 0:
                d = self._scan_device(self.cfg.deviceManageIp)
                d.addCallback(self.processTest)
                d.addErrback(self.handleExceptions)
                return d
            self._eventService.sendEvent(evt)
        return defer.succeed("Connected")

    def processTest(self, result):
        evt = result.getEvent()
        if evt:
            self._eventService.sendEvent(evt)
            if evt["severity"] != 0:
                return defer.succeed("Failed")

        return defer.succeed("Connected")

    def handleExceptions(self, reason):
        """
        Log internal exceptions that have occurred
        from testing TCP services

        @param reason: error message
        @type reason: Twisted error instance
        """
        msg = reason.getErrorMessage()
        evt = dict(
            device=self._preferences.options.monitor,
            summary=msg,
            severity=4,  # error
            component="zenstatus",
            traceback=reason.getTraceback(),
        )
        self._eventService.sendEvent(evt)
        return defer.succeed("Failed due to internal error")

    def cleanup(self):
        pass


#
# Collector Daemon Main entry point
#
if __name__ == "__main__":
    myPreferences = ZenStatusPreferences()
    myTaskFactory = SimpleTaskFactory(ZenStatusTask)
    myTaskSplitter = ServiceTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
