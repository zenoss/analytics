##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import re

from twisted.spread import pb

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenEvents import Event

# DeviceProxy must be present for twisted PB serialization to work.
from Products.ZenCollector.services.config import DeviceProxy  # noqa F401

log = logging.getLogger("zen.HubService.ProcessConfig")


class ProcessProxy(pb.Copyable, pb.RemoteCopy):
    """
    Track process-specific configuration data
    """

    name = None
    originalName = None
    restart = None
    includeRegex = None
    excludeRegex = None
    replaceRegex = None
    replacement = None
    primaryUrlPath = None
    generatedId = None
    severity = Event.Warning
    cycleTime = None
    processClass = None
    metadata = None

    def __init__(self):
        pass

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return str(self.name)

    __repr__ = __str__

    def processClassPrimaryUrlPath(self):
        return self.primaryUrlPath


pb.setUnjellyableForClass(ProcessProxy, ProcessProxy)


class ProcessConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        deviceProxyAttributes = ("zMaxOIDPerRequest",)
        CollectorConfigService.__init__(
            self, dmd, instance, deviceProxyAttributes
        )

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)
        include = include and device.snmpMonitorDevice()

        return include

    def _createDeviceProxy(self, device):
        procs = device.getMonitoredComponents(collector="zenprocess")
        if not procs:
            log.debug(
                "Device %s has no monitored processes -- ignoring",
                device.titleOrId(),
            )
            return None

        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = self.conf.processCycleInterval

        proxy.name = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.thresholds = []
        proxy.processes = {}
        proxy.snmpConnInfo = device.getSnmpConnInfo()
        for p in procs:
            # Find out which datasources are responsible for this process
            # if SNMP is not responsible, then do not add it to the list
            snmpMonitored = False
            for rrdTpl in p.getRRDTemplates():
                if len(rrdTpl.getRRDDataSources("SNMP")) > 0:
                    snmpMonitored = True
                    break

            # In case the process is not SNMP monitored
            if not snmpMonitored:
                log.debug(
                    "Skipping process %r - not an SNMP monitored process", p
                )
                continue
            # In case the catalog is out of sync above
            if not p.monitored():
                log.debug("Skipping process %r - zMonitor disabled", p)
                continue
            includeRegex = getattr(p.osProcessClass(), "includeRegex", False)
            excludeRegex = getattr(p.osProcessClass(), "excludeRegex", False)
            replaceRegex = getattr(p.osProcessClass(), "replaceRegex", False)
            replacement = getattr(p.osProcessClass(), "replacement", False)
            generatedId = getattr(p, "generatedId", False)
            primaryUrlPath = getattr(
                p.osProcessClass(), "processClassPrimaryUrlPath", False
            )
            if primaryUrlPath:
                primaryUrlPath = primaryUrlPath()

            if not includeRegex:
                log.warn(
                    "OS process class %s has no defined regex, "
                    "this process not being monitored",
                    p.getOSProcessClass(),
                )
                continue
            bad_regex = False
            for regex in [includeRegex, excludeRegex, replaceRegex]:
                if regex:
                    try:
                        re.compile(regex)
                    except re.error as ex:
                        log.warn(
                            "OS process class %s has an invalid regex (%s): "
                            "%s",
                            p.getOSProcessClass(),
                            regex,
                            ex,
                        )
                        bad_regex = True
                        break
            if bad_regex:
                continue

            proc = ProcessProxy()
            proc.metadata = p.getMetricMetadata()
            proc.includeRegex = includeRegex
            proc.excludeRegex = excludeRegex
            proc.replaceRegex = replaceRegex
            proc.replacement = replacement
            proc.primaryUrlPath = primaryUrlPath
            proc.generatedId = generatedId
            proc.name = p.id
            proc.originalName = p.name()
            proc.restart = p.alertOnRestart()
            proc.severity = p.getFailSeverity()
            proc.processClass = p.getOSProcessClass()
            proxy.processes[p.id] = proc
            proxy.thresholds.extend(p.getThresholdInstances("SNMP"))

        if proxy.processes:
            return proxy


if __name__ == "__main__":
    from Products.ZenHub.ServiceTester import ServiceTester

    tester = ServiceTester(ProcessConfig)

    def printer(config):
        for proc in config.processes.values():
            print("\t".join([proc.name, str(proc.includeRegex)]))

    tester.printDeviceProxy = printer
    tester.showDeviceInfo()
