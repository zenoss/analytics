##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import sys

import zope.component

from twisted.internet import reactor, error, defer
from twisted.python import failure
from twisted.internet.error import TimeoutError
from pynetsnmp.twistedsnmp import snmpprotocol, SnmpUsmError

from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp
from Products.ZenHub.interfaces import IEventService
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.snmp import (
    SnmpAgentDiscoverer,
    SnmpV1Config,
    SnmpV2cConfig,
)

from .BaseClient import BaseClient

defaultTries = 2
defaultTimeout = 1
defaultSnmpCommunity = "public"

DEFAULT_MAX_OIDS_BACK = 40

STATUS_EVENT = {"eventClass": Status_Snmp, "eventGroup": "SnmpTest"}

log = logging.getLogger("zen.SnmpClient")


class SnmpClient(BaseClient):
    def __init__(
        self,
        hostname,
        ipaddr,
        options=None,
        device=None,
        datacollector=None,
        plugins=None,
    ):
        super(SnmpClient, self).__init__(device, datacollector)
        global defaultTries, defaultTimeout
        self.hostname = hostname
        self.device = device
        self.options = options
        self.datacollector = datacollector
        self.plugins = plugins if plugins else []

        self._getdata = {}
        self._tabledata = {}

        from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo

        self.connInfo = SnmpConnInfo(device)
        self.proxy = None
        self._eventService = zope.component.queryUtility(IEventService)

    def initSnmpProxy(self):
        if self.proxy is not None:
            self.proxy.close()
        srcport = snmpprotocol.port()
        try:
            self.proxy = self.connInfo.createSession(srcport.protocol)
            self.proxy.open()
        except Exception as ex:
            log.error("failed to initialize SNMP session  error=%s", ex)
            self.proxy = None

    def run(self):
        """Start snmp collection."""
        log.debug("starting  %s", self.connInfo.summary())
        self.initSnmpProxy()
        drive(self.doRun).addBoth(self.clientFinished)

    # FIXME: cleanup --force option #2660
    def checkCiscoChange(self, driver):
        """Check to see if a cisco box has changed."""
        device = self.device
        yield self.proxy.get([".1.3.6.1.4.1.9.9.43.1.1.1.0"])
        lastpolluptime = device.getLastPollSnmpUpTime()
        log.debug("lastpolluptime = %s", lastpolluptime)
        result = True
        try:
            lastchange = driver.next().values()[0]
            log.debug("lastchange = %s", lastchange)
            if lastchange <= lastpolluptime:
                log.info(
                    "skipping cisco device %s no change detected", device.id
                )
                result = False
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except Exception as ex:
            log.debug("failed to check Cisco change: %s", ex)
        yield defer.succeed(result)

    def doRun(self, driver):
        if self.proxy is None:
            return
        # test snmp connectivity
        log.debug("Testing SNMP configuration")
        yield self.proxy.walk(".1.3")
        try:
            driver.next()
        except TimeoutError:
            log.info("device timed out  %s", self.connInfo.summary())
            if self.options.discoverCommunity:
                yield self.findSnmpCommunity()
                snmp_config = driver.next()
                if not snmp_config:
                    log.error(
                        "Failed to rediscover the SNMP connection info for %s",
                        self.device.manageIp,
                    )
                    raise
                if snmp_config.version:
                    self.connInfo.zSnmpVer = snmp_config.version
                if snmp_config.port:
                    self.connInfo.zSnmpPort = snmp_config.port
                if snmp_config.community:
                    self.connInfo.zSnmpCommunity = snmp_config.community
                self.connInfo.changed = True
                self.initSnmpProxy()
            else:
                raise
        except SnmpUsmError as ex:
            log.error(
                "cannot connect to SNMP agent  error=%s %s",
                ex, self.connInfo.summary()
            )
            raise
        except Exception:
            log.exception("unable to talk  %s", self.connInfo.summary())
            raise

        changed = True
        # FIXME: cleanup --force option #2660
        if not self.options.force and self.device.snmpOid.startswith(
            ".1.3.6.1.4.1.9"
        ):
            yield drive(self.checkCiscoChange)
            changed = driver.next()
        if changed:
            yield drive(self.collect)

    def findSnmpCommunity(self):
        def inner(driver):
            """
            Twisted driver class to iterate through devices

            @param driver: Zenoss driver
            @type driver: Zenoss driver
            @return: successful result is a list of IPs that were added
            @rtype: Twisted deferred
            """
            log.info(
                "Rediscovering SNMP connection info for %s", self.device.id
            )

            communities = list(self.device.zSnmpCommunities)
            communities.reverse()

            ports = self.device.zSnmpDiscoveryPorts
            ports = ports if ports else [self.device.zSnmpPort]

            configs = []
            weight = 0
            for community in communities:
                for port in ports:
                    weight += 1
                    port = int(port)
                    configs.append(
                        SnmpV1Config(
                            self.device.manageIp,
                            weight=weight,
                            port=port,
                            timeout=self.connInfo.zSnmpTimeout,
                            retries=self.connInfo.zSnmpTries,
                            community=community,
                        )
                    )
                    configs.append(
                        SnmpV2cConfig(
                            self.device.manageIp,
                            weight=weight + 1000,
                            port=port,
                            timeout=self.connInfo.zSnmpTimeout,
                            retries=self.connInfo.zSnmpTries,
                            community=community,
                        )
                    )

            yield SnmpAgentDiscoverer().findBestConfig(configs)
            driver.next()

        return drive(inner)

    def collect(self, driver):
        maxOidsPerRequest = getattr(
            self.device, "zMaxOIDPerRequest", DEFAULT_MAX_OIDS_BACK
        )
        log.debug("Using a max of %s OIDs per request", maxOidsPerRequest)
        for plugin in self.plugins:
            try:
                log.debug("running %s", plugin)
                pname = plugin.name()
                self._tabledata[pname] = {}
                log.debug("sending queries for plugin %s", pname)
                if plugin.snmpGetMap:
                    results = {}
                    for oid in plugin.snmpGetMap.getoids():
                        yield self.proxy.get([oid])
                        results.update(driver.next())
                    self._getdata[pname] = results
                for tmap in plugin.snmpGetTableMaps:
                    rowSize = len(tmap.getoids())
                    maxRepetitions = max(maxOidsPerRequest / rowSize, 1)
                    yield self.proxy.getTable(
                        tmap.getoids(),
                        maxRepetitions=maxRepetitions,
                        limit=sys.maxint,
                    )
                    self._tabledata[pname][tmap] = driver.next()
            except error.TimeoutError:
                log.error("%s %s SNMP timeout", self.device.id, pname)
            except Exception:
                log.exception(
                    "device %s plugin %s unexpected error",
                    self.hostname,
                    pname,
                )

    def getResults(self):
        """Return data for this client in the form
        ((plugin, (getdata, tabledata),)
        getdata = {'.1.2.4.5':"value",}
        tabledata = {tableMap : {'.1.2.3.4' : {'.1.2.3.4.1': "value",...}}}
        """
        data = []
        for plugin in self.plugins:
            pname = plugin.name()
            getdata = self._getdata.get(pname, {})
            tabledata = self._tabledata.get(pname, {})
            if getdata or tabledata:
                data.append((plugin, (getdata, tabledata)))
        return data

    def _sendStatusEvent(self, summary, eventKey=None, severity=Event.Error):
        self._eventService.sendEvent(
            STATUS_EVENT.copy(),
            severity=severity,
            device=self.device.id,
            eventKey=eventKey,
            summary=summary,
        )

    def clientFinished(self, result):
        log.info("snmp client finished collection for %s", self.hostname)
        if isinstance(result, failure.Failure):
            from twisted.internet import error

            if isinstance(result.value, error.TimeoutError):
                log.error(
                    "device %s timed out: are your SNMP settings correct?",
                    self.hostname,
                )
                summary = "SNMP agent down - no response received"
                log.info("Sending event: %s", summary)
            elif isinstance(result.value, SnmpUsmError):
                log.error(
                    "SNMP connection failed  device=%s error=%s",
                    self.hostname,
                    result.value,
                )
                summary = "SNMP v3 specific error during SNMP collection"
            else:
                log.exception(
                    "Device %s had an error: %s", self.hostname, result
                )
                summary = "Exception during SNMP collection"
            self._sendStatusEvent(summary, eventKey="agent_down")
        else:
            self._sendStatusEvent(
                "SNMP agent up",
                eventKey="agent_down",
                severity=Event.Clear,
            )
        try:
            self.proxy.close()
        except AttributeError:
            log.info("caught AttributeError closing SNMP connection.")
        if self.datacollector:
            self.datacollector.clientFinished(self)
        else:
            reactor.stop()

    def stop(self):
        self.proxy.close()
