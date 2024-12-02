##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import zope.component
import zope.interface

from zope.event import notify

import Products.ZenStatus.interfaces

from Products.ZenCollector import interfaces

# perform some imports to allow twisted's PB to serialize these objects
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.PingPerformanceConfig import (
    PingPerformanceConfig,
)
from Products.ZenUtils.Utils import unused

from .interfaces import IParserReadyForOptionsEvent

unused(DeviceProxy)
unused(PingPerformanceConfig)

log = logging.getLogger("zen.zenping.pingcollectionprefs")

# define some constants strings
COLLECTOR_NAME = "zenping"
CONFIG_SERVICE = "Products.ZenHub.services.PingPerformanceConfig"


@zope.interface.implementer(IParserReadyForOptionsEvent)
class ParserReadyForOptionsEvent(object):
    def __init__(self, parser):
        self.parser = parser


@zope.interface.implementer(interfaces.ICollectorPreferences)
class PingCollectionPreferences(object):
    def __init__(self):
        """
        Constructs a new PingCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.configCycleInterval = 20  # minutes
        self.cycleInterval = 60 * 5  # seconds

        # do not pause our tasks, when devices are determined down
        self.pauseUnreachableDevices = False

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = CONFIG_SERVICE

        # Will be filled in based on buildOptions
        self.options = None

        self.pingTimeOut = 1.5
        self.pingTries = 2
        self.pingChunk = 75
        self.pingCycleInterval = 60

    def buildOptions(self, parser):
        parser.add_option(
            "--disable-correlator",
            dest="disableCorrelator",
            default=False,
            action="store_true",
            help="Disable the ping down event correlator.",
        )

        parser.add_option(
            "--traceroute-interval",
            dest="tracerouteInterval",
            default=5,
            type="int",
            help="Traceroute every N ping intervals; default is 5, "
            "traceroute every time a ping is performed.",
        )
        parser.add_option(
            "--data-length",
            dest="dataLength",
            default=0,
            type="int",
            help="Length of datapacket for zenping to use (default: %default)",
        )

        parser.add_option(
            "--delay-count",
            dest="delayCount",
            default=0,
            type="int",
            help="Delay down events until more than this many ping downs "
            "are collected in a row. Default is 0 (no delay).",
        )

        parser.add_option(
            "--connected-ips",
            type="choice",
            action="store",
            choices=["enabled", "disabled"],
            default="disabled",
            help="Use IPs connected to a device for ping correlation "
            "(default: %default)",
        )

        # look up possible ping backends
        pingBackends = []
        for pingBackend, _ in zope.component.getUtilitiesFor(
            Products.ZenStatus.interfaces.IPingTaskFactory
        ):
            pingBackends.append(pingBackend)
        backendsHelp = "ping backend to use (%s)" % ", ".join(pingBackends)
        parser.add_option(
            "--ping-backend",
            dest="pingBackend",
            default="nmap",
            help=backendsHelp + " default: %default",
        )

        # look up possible correlation backends
        correlationBackends = []
        for correlationBackend, _ in zope.component.getUtilitiesFor(
            Products.ZenStatus.interfaces.IPingTaskCorrelator
        ):
            correlationBackends.append(correlationBackend)
        correlationBackendsHelp = "Correlationbackend to use (%s)" % ", ".join(
            correlationBackends
        )
        parser.add_option(
            "--correlation-backend",
            dest="correlationBackend",
            default=correlationBackend,  # last registed backend is default
            help=correlationBackendsHelp + " default: %default",
        )

        # allow extention points to add options
        notify(ParserReadyForOptionsEvent(parser))

    def postStartup(self):
        pass

    def preShutdown(self):
        pass
