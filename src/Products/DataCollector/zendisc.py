##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# IMPORTANT! The import of the pysamba.twisted.reactor module should come
# before any other libraries that might possibly use twisted. This will
# ensure that the proper WmiReactor is installed before anyone else grabs
# a reference to the wrong reactor.
try:
    import pysamba.twisted.reactor  # noqa F401
except ImportError:
    pass

import logging
import socket

from optparse import SUPPRESS_HELP

import six

from twisted.internet import defer
from twisted.names.error import DNSNameError

from Products.DataCollector.zenmodeler import ZenModeler
from Products.ZenEvents.Event import Info
from Products.ZenEvents.ZenEventClasses import Status_Snmp
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenHub.services import DiscoverService, ModelerService
from Products.ZenHub.services.DiscoverService import JobPropertiesProxy
from Products.ZenModel.Exceptions import NoIPAddress
from Products.ZenStatus.nmap.util import executeNmapForIps
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenUtils.IpUtil import (
    asyncNameLookup,
    getHostByName,
    ipunwrap,
    isip,
    parse_iprange,
)
from Products.ZenUtils.snmp import (
    SnmpAgentDiscoverer,
    SnmpV1Config,
    SnmpV2cConfig,
    SnmpV3Config,
)
from Products.ZenUtils.Utils import unused

unused(DiscoverService, ModelerService, JobPropertiesProxy)

DEFAULT_COMMUNITIES = ["public", "private"]


def _partitionPingResults(results):
    """Groups the results into a 'good' results and 'bad' results and
    returns each set as a tuple.

    @returns {tuple} (<good-results>, <bad-results>)
    """
    good, bad = [], []
    for result in results:
        if result.isUp:
            good.append(result.address)
        else:
            bad.append(result.address)
    return (good, bad)


# From ZenRRD/zenprocess.py; should move into ZenUtils somewhere
def chunk(lst, n):
    """
    Break lst into n-sized chunks
    """
    return (lst[i : i + n] for i in range(0, len(lst), n))


class ZenDisc(ZenModeler):
    """
    Scan networks and routes looking for devices to add to the ZODB
    """

    initialServices = PBDaemon.initialServices + ["DiscoverService"]
    mname = name = "zendisc"
    scanned = 0

    def __init__(self, single=True):
        """
        Initalizer

        @param single: collect from a single device?
        @type single: boolean
        """
        ZenModeler.__init__(self, single)
        self.discovered = []

    def config(self):
        """
        Get the DiscoverService

        @return: a DiscoverService from zenhub
        @rtype: function
        """
        return self.services.get("DiscoverService", FakeRemote())

    @defer.inlineCallbacks
    def pingMany(self, ipList):
        """
        Given a list of IP addresses, return a list containing the
        results of pinging each of those addresses.
        """
        results = yield executeNmapForIps(sorted(ipList))
        self.log.info("Found %s addresses", len(results))
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug(
                "Addresses found: %s", ", ".join(a for a in results)
            )
        defer.returnValue(results.values())

    @defer.inlineCallbacks
    def discoverIps(self, nets):
        """
        Ping all ips, create entries in the network if necessary.

        @param nets {list} list of networks to discover
        @return: successful result is a list of IPs that were added
        @rtype: Twisted deferred
        """
        ips = []
        for net in nets:
            if self.options.subnets and len(net.children()) > 0:
                continue
            if not getattr(net, "zAutoDiscover", False):
                self.log.info(
                    "Skipping network %s because zAutoDiscover is False",
                    net.getNetworkName(),
                )
                continue
            self.log.info("Discover network '%s'", net.getNetworkName())

            full_ip_list = net.fullIpList()
            if self.options.removeInterfaceIps:
                full_ip_list = yield self.config().callRemote(
                    "removeInterfaces", net
                )

            results = yield self.pingMany(full_ip_list)
            goodips, badips = _partitionPingResults(results)
            self.log.debug(
                "Found %d good IPs and %d bad IPs", len(goodips), len(badips)
            )
            yield self.config().callRemote(
                "pingStatus",
                net,
                goodips,
                badips,
                self.options.resetPtr,
                self.options.addInactive,
            )
            ips += goodips
            self.log.info("Discovered %s active ips", len(ips))
        defer.returnValue(ips)

    @defer.inlineCallbacks
    def discoverRanges(self):
        """
        Ping all IPs in the range and create devices for the ones that come
        back.
        """
        iprange = self.options.range
        if isinstance(iprange, six.string_types):
            iprange = [iprange]
        # in case someone uses 10.0.0.0-5,192.168.0.1-5 instead of
        # --range 10.0.0.0-5 --range 192.168.0.1-5
        if isinstance(iprange, list) and iprange[0].find(",") > -1:
            iprange = [n.strip() for n in iprange[0].split(",")]
        ips = []
        for rangelimit in iprange:
            # Parse to find ips included
            ips.extend(parse_iprange(rangelimit))
        results = yield self.pingMany(ips)
        goodips, badips = _partitionPingResults(results)
        self.log.debug(
            "Found %d good IPs and %d bad IPs", len(goodips), len(badips)
        )
        self.log.info("Discovered %d active IPs", len(goodips))
        devices = yield self.discoverDevices(goodips)
        defer.returnValue(devices)

    @defer.inlineCallbacks
    def discoverRouters(self, rootdev):
        """
        Discover all default routers based on DMD configuration.

        @param rootdev {device class} device root in DMD
        """
        observedIps = set()
        routers = [rootdev]
        while routers:
            router = routers.pop(0)
            ips = yield self.config().callRemote("followNextHopIps", router.id)
            unknownIps = (ip for ip in ips if ip not in observedIps)
            for batch_of_ips in chunk(unknownIps, self.options.parallel):
                results = yield defer.DeferredList(
                    self.discoverDevice(ip, devicepath="/Network/Router")
                    for ip in batch_of_ips
                )
                observedIps.update(batch_of_ips)
                routers.extend(
                    foundRouter
                    for _, foundRouter in results
                    if foundRouter is not None
                )

    def sendDiscoveredEvent(self, ip, dev=None, sev=2):
        """
        Send a 'device discovered' event through zenhub

        @param ip: IP addresses
        @type ip: strings
        @param dev: remote device name
        @type dev: device object
        @param sev: severity
        @type sev: integer
        """
        devname = comp = ip
        if dev:
            devname = dev.id
        msg = "Discovered device name '%s' for ip '%s'" % (devname, ip)
        evt = {
            "device": devname,
            "ipAddress": ip,
            "eventKey": ip,
            "component": comp,
            "eventClass": Status_Snmp,
            "summary": msg,
            "severity": sev,
            "agent": "Discover",
        }
        self.sendEvent(evt)

    @defer.inlineCallbacks
    def discoverDevices(self, ips, devicepath=None, prodState=None):
        """
        Discover devices by active ips that are not associated with a device.

        @param ips: list of IP addresses
        @type ips: list of strings
        @param devicepath: where in the DMD to put any discovered devices
        @type devicepath: string
        @param prodState: production state (see Admin Guide for a description)
        @type prodState: integer
        @return: Twisted/Zenoss Python iterable
        @rtype: Python iterable
        """
        if devicepath is None:
            devicepath = self.options.deviceclass
        if prodState is None:
            prodState = self.options.productionState
        foundDevices = []
        for batch_of_ips in chunk(ips, self.options.parallel):
            results = yield defer.DeferredList(
                self.discoverDevice(ip, devicepath, prodState)
                for ip in batch_of_ips
            )
            discovered = [dev for _, dev in results if dev is not None]
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug(
                    "Discovered %s devices: %s",
                    len(discovered),
                    ", ".join(dev.getId() for dev in discovered),
                )
            foundDevices.extend(discovered)
        defer.returnValue(foundDevices)

    @defer.inlineCallbacks
    def findRemoteDeviceInfo(self, ip, devicePath, deviceSnmpCommunities=None):
        """
        Scan a device for ways of naming it: PTR DNS record or a SNMP name

        @param ip: IP address
        @type ip: string
        @param devicePath: where in the DMD to put any discovered devices
        @type devicePath: string
        @param deviceSnmpCommunities: Optional list of SNMP community strings
            to try, overriding those set on the device class
        @type deviceSnmpCommunities: list
        @return: result is None or a tuple containing
            (community, port, version, snmp name)
        @rtype: deferred: Twisted deferred
        """
        self.log.debug("Doing SNMP lookup on device %s", ip)
        snmp_conf = yield self.config().callRemote(
            "getDeviceClassSnmpConfig", devicePath
        )

        configs = []
        ports = snmp_conf.get("zSnmpDiscoveryPorts") or [
            snmp_conf["zSnmpPort"]
        ]
        timeout, retries = snmp_conf["zSnmpTimeout"], snmp_conf["zSnmpTries"]
        if snmp_conf["zSnmpVer"] == SnmpV3Config.version:
            for port in ports:
                engine = snmp_conf.get("zSnmpEngineId")
                context = snmp_conf.get("zSnmpContext")

                common_params = {
                    "ip": ip,
                    "port": port,
                    "timeout": timeout,
                    "retries": retries,
                    "securityName": snmp_conf["zSnmpSecurityName"],
                }

                if engine:
                    common_params["engine"] = engine
                if context:
                    common_params["context"] = context

                if snmp_conf["zSnmpPrivType"] and snmp_conf["zSnmpAuthType"]:
                    params = common_params.copy()
                    params.update({
                        "authType": snmp_conf["zSnmpAuthType"],
                        "authPassphrase": snmp_conf["zSnmpAuthPassword"],
                        "privType": snmp_conf["zSnmpPrivType"],
                        "privPassphrase": snmp_conf["zSnmpPrivPassword"],
                        "weight": 3,
                    })
                    configs.append(SnmpV3Config(**params))
                elif snmp_conf["zSnmpAuthType"]:
                    params = common_params.copy()
                    params.update({
                        "authType": snmp_conf["zSnmpAuthType"],
                        "authPassphrase": snmp_conf["zSnmpAuthPassword"],
                        "weight": 2,
                    })
                    configs.append(SnmpV3Config(**params))
                else:
                    params = common_params.copy()
                    params["weight"] = 1
                    configs.append(SnmpV3Config(**params))
        else:
            self.log.debug("Override acquired community strings")
            # Use a default set of SNMP community strings if the device
            # class has none configured.
            communities = snmp_conf["zSnmpCommunities"] or DEFAULT_COMMUNITIES

            # If they exist, use this device's SNMP community strings instead
            # of the strings from the device class.
            if deviceSnmpCommunities:
                communities = deviceSnmpCommunities

            # Reverse the communities so that ones earlier in the list have a
            # higher weight.
            communities.reverse()

            for i, community in enumerate(communities):
                for port in ports:
                    port = int(port)
                    configs.append(
                        SnmpV1Config(
                            ip,
                            weight=i,
                            port=port,
                            timeout=timeout,
                            retries=retries,
                            community=community,
                        )
                    )
                    configs.append(
                        SnmpV2cConfig(
                            ip,
                            weight=i + 100,
                            port=port,
                            timeout=timeout,
                            retries=retries,
                            community=community,
                        )
                    )

        config = yield SnmpAgentDiscoverer().findBestConfig(configs)

        self.log.debug("Finished SNMP lookup on device %s", ip)
        defer.returnValue(config)

    @defer.inlineCallbacks
    def discoverDevice(
        self, ip, devicepath=None, prodState=None, deviceConfig=None
    ):
        """
        Discover the device at the given IP address.

        @param ip: IP address
        @type ip: string
        @param devicepath: where in the DMD to put any discovered devices
        @type devicepath: string
        @param prodState: production state (see Admin Guide for a description)
        @type prodState: integer
        @return: Twisted/Zenoss Python iterable
        @rtype: Python iterable
        """
        if devicepath is None:
            devicepath = self.options.deviceclass
        if prodState is None:
            prodState = self.options.productionState

        self.scanned += 1
        if self.options.maxdevices:
            if self.scanned >= self.options.maxdevices:
                self.log.info(
                    "Limit of %d devices reached", self.options.maxdevices
                )
                defer.returnValue(None)

        try:
            kw = {
                "deviceName": ip,
                "discoverProto": None,
                "devicePath": devicepath,
                "performanceMonitor": self.options.monitor,
                "locationPath": self.options.location,
                "groupPaths": self.options.groups,
                "systemPaths": self.options.systems,
                "productionState": prodState,
            }

            # If zProperties are set via a job, get them and pass them in
            if self.options.job:
                job_props = yield self.config().callRemote(
                    "getJobProperties", self.options.job
                )
                if job_props is not None:
                    # grab zProperties from Job
                    kw["zProperties"] = getattr(job_props, "zProperties", {})
                    # grab other Device properties from jobs
                    # deviceProps = job_props.get('deviceProps', {})
                    # kw.update(deviceProps)
                    # @FIXME we are not getting deviceProps, check calling
                    #  chain for clues. twisted upgrade heartburn perhaps?

            # if we are using SNMP, lookup the device SNMP info and use the
            # name defined there for deviceName
            if not self.options.nosnmp:
                self.log.debug("Scanning device with address %s", ip)
                zProps = kw.get("zProperties", {})
                deviceSnmpCommunities = zProps.get("zSnmpCommunities", None)
                if not deviceSnmpCommunities and deviceConfig:
                    deviceSnmpCommunities = getattr(
                        deviceConfig, "zSnmpCommunities", None
                    )

                snmp_config = yield self.findRemoteDeviceInfo(
                    ip, devicepath, deviceSnmpCommunities
                )
                if snmp_config:
                    if snmp_config.sysName:
                        kw["deviceName"] = snmp_config.sysName
                    if snmp_config.version:
                        kw["zSnmpVer"] = snmp_config.version
                    if snmp_config.port:
                        kw["zSnmpPort"] = snmp_config.port
                    if snmp_config.community:
                        kw["zSnmpCommunity"] = snmp_config.community

                # Since we did not find any snmp info and we are in
                # strict discovery mode, do not create a device
                elif self.options.zSnmpStrictDiscovery:
                    self.log.info(
                        "zSnmpStrictDiscovery is True. "
                        "Not creating device for %s.",
                        ip,
                    )
                    defer.returnValue(None)

            # RULES FOR DEVICE NAMING:
            # 1. If zPreferSnmpNaming is true:
            #        If snmp name is returned, use snmp name. Otherwise,
            #        use the passed device name.  If no device name was passed,
            #        do a dns lookup on the ip.
            # 2. If zPreferSnmpNaming is false:
            #        If we are discovering a single device and a name is
            #        passed in instead of an IP, use the passed-in name.
            #        Otherwise, do a dns lookup on the ip.
            if self.options.zPreferSnmpNaming and not isip(kw["deviceName"]):
                # In this case, we want to keep kw['deviceName'] as-is,
                # because it is what we got from snmp
                pass
            elif self.options.device and not isip(self.options.device):
                kw["deviceName"] = self.options.device
            else:
                # An IP was passed in so we do a reverse lookup on it to get
                # deviceName
                try:
                    kw["deviceName"] = yield asyncNameLookup(ip)
                except Exception as ex:
                    self.log.debug("Failed to lookup %s (%s)", ip, ex)

            # If it's discovering a particular device,
            # ignore zAutoDiscover limitations
            forceDiscovery = bool(self.options.device)

            # now create the device by calling zenhub
            result = None
            try:
                result = yield self.config().callRemote(
                    "createDevice", ipunwrap(ip), force=forceDiscovery, **kw
                )
            except Exception as ex:
                raise ZentinelException(ex)

            self.log.debug("Got result from remote_createDevice: %s", result)
            dev, created = result

            # if no device came back from createDevice we assume that it
            # was told to not auto-discover the device.  This seems very
            # dubious to me! -EAD
            if not dev:
                self.log.info("IP '%s' on no auto-discover, skipping", ip)
                defer.returnValue(None)

            # A device came back and it already existed.
            if not created and not dev.temp_device:
                # if we shouldn't remodel skip the device by returning
                # at the end of this block
                if not self.options.remodel:
                    self.log.info(
                        "Found IP '%s' on device '%s';" " skipping discovery",
                        ip,
                        dev.id,
                    )
                    if self.options.device:
                        self.setExitCode(3)
                    defer.returnValue(dev)
                else:
                    # we continue on to model the device.
                    self.log.info("IP '%s' on device '%s' remodel", ip, dev.id)
            self.sendDiscoveredEvent(ip, dev)

            # the device that we found/created or that should be remodeled
            # is added to the list of devices to be modeled later
            if not self.options.nosnmp:
                self.discovered.append(dev.id)

            yield self.config().callRemote("succeedDiscovery", dev.id)
            defer.returnValue(dev)
        except ZentinelException as e:
            self.log.exception(e)
            if self.options.snmpMissing:
                self.sendEvent(
                    {
                        "device": ip,
                        "component": ip,
                        "ipAddress": ip,
                        "eventKey": ip,
                        "eventClass": Status_Snmp,
                        "summary": str(e),
                        "severity": Info,
                        "agent": "Discover",
                    }
                )
        except Exception:
            self.log.exception("Failed device discovery for '%s'", ip)
        finally:
            self.log.info("Finished scanning device with address %s", ip)

    @defer.inlineCallbacks
    def collectNet(self):
        """
        Twisted driver class to iterate through networks

        @param driver: Zenoss driver
        @type driver: Zenoss driver
        @return: successful result is a list of IPs that were added
        @rtype: Twisted deferred
        """
        network = self.options.net
        # net option from the config file is a string
        if isinstance(network, six.string_types):
            network = [network]
        # in case someone uses 10.0.0.0,192.168.0.1 instead of
        # --net 10.0.0.0 --net 192.168.0.1
        if isinstance(network, (list, tuple)) and "," in network[0]:
            network = [n.strip() for n in network[0].split(",")]
        if not network:
            network = yield self.config().callRemote("getDefaultNetworks")
        if not network:
            self.log.warning("No networks configured")
            defer.returnValue([])

        foundIps = []
        for net in network:
            try:
                nets = yield self.config().callRemote(
                    "getNetworks", net, self.options.subnets
                )
                if not nets:
                    self.log.warning("No networks found for %s", net)
                    continue
                foundIps += yield self.discoverIps(nets)
            except Exception as ex:
                self.log.exception(
                    "Error performing net discovery on %s: %s", net, ex
                )
        self.log.info("Working on devices: %s", foundIps)

        foundDevices = yield self.discoverDevices(
            foundIps,
            devicepath=self.options.deviceclass,
            prodState=self.options.productionState,
        )
        defer.returnValue(foundDevices)

    @defer.inlineCallbacks
    def createDevice(self):
        """
        Add a device to the system by name or IP.
        """
        deviceName = self.options.device
        self.log.info("Looking for %s", deviceName)
        ip = ipunwrap(deviceName)
        if not isip(ip):
            try:
                ip = yield getHostByName(deviceName)
            except socket.error as ex:
                self.log.warn(
                    "Hostname lookup failed for %s: %s", deviceName, ex
                )
                raise NoIPAddress("No IP found for name %s" % deviceName)
        self.log.info("Found IP %s for device %s", ip, deviceName)
        configs = yield self.config().callRemote(
            "getDeviceConfig", [deviceName]
        )
        config = configs[0] if configs else None
        if not config or config.temp_device or self.options.remodel:
            device = yield self.discoverDevice(
                ip,
                devicepath=self.options.deviceclass,
                prodState=self.options.productionState,
                deviceConfig=config,
            )
            if device:
                self.log.info("Discovered device %s.", device.id)
            else:
                self.log.info("Device '%s' not found", deviceName)
            defer.returnValue(device)
        else:
            self.log.info("Device '%s' already found", deviceName)

    @defer.inlineCallbacks
    def walkDiscovery(self):
        """
        Python iterable to go through discovery
        """
        myname = socket.getfqdn()
        self.log.debug("My hostname = %s", myname)
        myip = None
        try:
            myip = getHostByName(myname)  # not async; blocks reactor!
            self.log.debug("My IP address = %s", myip)
        except (socket.error, DNSNameError):
            raise SystemExit("Failed lookup of my IP for name %s" % myname)
        configs = yield self.config().callRemote("getDeviceConfig", [myname])
        me = configs[0] if configs else None
        if not me or self.options.remodel:
            me = yield self.discoverDevice(
                myip,
                devicepath=self.options.deviceclass,
                prodState=self.options.productionState,
            )
        if not me:
            raise SystemExit("SNMP discover of self '%s' failed" % myname)
        if not myip:
            myip = me.manageIp
        if not myip:
            raise SystemExit("Can't find my IP for name %s" % myname)

        yield self.discoverRouters(me, [myip])

        if self.options.routersonly:
            self.log.info("Only routers discovered, skipping ping sweep.")
            defer.returnValue(None)

        ips = yield self.discoverIps(
            (yield self.config().callRemote("getSubNetworks"))
        )
        if not self.options.nosnmp:
            defer.returnValue((yield self.discoverDevices(ips)))
        defer.returnValue(ips)

    def getDeviceList(self):
        """
        Our device list comes from our list of newly discovered devices

        @return: list of discovered devices
        @rtype: Twisted succeed() object
        """
        return defer.succeed(self.discovered)

    def connected(self):
        """
        Called by Twisted once a connection has been established.
        """
        d = self.configure()
        d.addCallback(self.startDiscovery)
        d.addErrback(self.reportError)

    @defer.inlineCallbacks
    def startDiscovery(self, data):
        try:
            if self.options.walk:
                results = yield self.walkDiscovery()
            elif self.options.device:
                results = yield self.createDevice()
                if results:
                    results = results.getId()
            elif self.options.range:
                results = [d.getId() for d in (yield self.discoverRanges())]
            else:
                results = [d.getId() for d in (yield self.collectNet())]
            self.log.info("Result: %s", results)
        except NoIPAddress as ex:
            self.log.error("Error: %s", ex)
        except Exception as ex:
            self.log.exception(ex)
        self.main()

    def buildOptions(self):
        """
        Command-line option builder for optparse
        """
        ZenModeler.buildOptions(self)
        self.parser.add_option(
            "--net",
            dest="net",
            action="append",
            help="Discover all device on this network",
        )
        self.parser.add_option(
            "--range",
            dest="range",
            action="append",
            help="Discover all IPs in this range",
        )
        self.parser.add_option(
            "--deviceclass",
            dest="deviceclass",
            default="/Discovered",
            help="Default device class for discovered devices",
        )
        self.parser.add_option(
            "--prod_state",
            dest="productionState",
            default=1000,
            type="int",
            help="Initial production state for discovered devices",
        )
        self.parser.add_option(
            "--prod-state",
            dest="productionState",
            default=1000,
            type="int",
            help="Initial production state for discovered devices",
        )
        self.parser.add_option(
            "--location",
            dest="location",
            default=None,
            help="Initial location for discovered devices",
        )
        self.parser.add_option(
            "--group",
            dest="groups",
            action="append",
            help="Group to which discovered devices should be added",
        )
        self.parser.add_option(
            "--system",
            dest="systems",
            action="append",
            help="System to which discovered devices should be added",
        )
        self.parser.add_option(
            "--remodel",
            dest="remodel",
            action="store_true",
            default=False,
            help="Remodel existing objects",
        )
        self.parser.add_option(
            "--routers",
            dest="routersonly",
            action="store_true",
            default=False,
            help="Only discover routers",
        )
        self.parser.add_option(
            "--tries",
            dest="tries",
            default=1,
            type="int",
            help="How many ping tries",
        )
        self.parser.add_option(
            "--timeout",
            dest="timeout",
            default=2,
            type="float",
            help="ping timeout in seconds",
        )
        self.parser.add_option(
            "--chunk",
            dest="chunkSize",
            default=10,
            type="int",
            help="Number of in-flight ping packets",
        )
        self.parser.add_option(
            "--snmp-missing",
            dest="snmpMissing",
            action="store_true",
            default=False,
            help="Send an event if SNMP is not found on the device",
        )
        self.parser.add_option(
            "--add-inactive",
            dest="addInactive",
            action="store_true",
            default=False,
            help="Add all IPs found, even if they are unresponsive",
        )
        self.parser.add_option(
            "--reset-ptr",
            dest="resetPtr",
            action="store_true",
            default=False,
            help="Reset all IP PTR records",
        )
        self.parser.add_option(
            "--no-snmp",
            dest="nosnmp",
            action="store_true",
            default=False,
            help="Skip SNMP discovery on found IP addresses",
        )
        self.parser.add_option(
            "--subnets",
            dest="subnets",
            action="store_true",
            default=False,
            help="Recurse into subnets for discovery",
        )
        self.parser.add_option(
            "--walk",
            dest="walk",
            action="store_true",
            default=False,
            help="Walk the route tree, performing discovery on all networks",
        )
        self.parser.add_option(
            "--max-devices",
            dest="maxdevices",
            default=0,
            type="int",
            help="Collect a maximum number of devices. Default is no limit.",
        )
        self.parser.add_option(
            "--snmp-strict-discovery",
            dest="zSnmpStrictDiscovery",
            action="store_true",
            default=False,
            help="Only add devices that can be modeled via SNMP.",
        )
        self.parser.add_option(
            "--prefer-snmp-naming",
            dest="zPreferSnmpNaming",
            action="store_true",
            default=False,
            help="Prefer SNMP name to DNS name when modeling via SNMP.",
        )
        self.parser.add_option(
            "--remove-interface-ips",
            dest="removeInterfaceIps",
            action="store_true",
            default=False,
            help="Skip discovery on IPs already assigned to interfaces "
            "(device components).",
        )

        # --job: a development-only option that jobs will use to communicate
        # their existence to zendisc. Not for users, so help is suppressed.
        self.parser.add_option("--job", dest="job", help=SUPPRESS_HELP)


if __name__ == "__main__":
    d = ZenDisc()
    d.processOptions()
    d.run()
