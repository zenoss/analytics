##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""RRDDaemon

Common performance monitoring daemon code for performance daemons.
"""

import socket

from twisted.python import failure

from Products.ZenEvents import Event
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon

from .Thresholds import Thresholds

BAD_SEVERITY = Event.Warning

BASE_URL = "http://localhost:8080/zport/dmd"
DEFAULT_URL = BASE_URL + "/Monitors/Performance/localhost"

COMMON_EVENT_INFO = {
    "manager": socket.getfqdn(),
}


class RRDDaemon(PBDaemon):
    """
    Holds the code common to performance gathering daemons.
    """

    properties = ("configCycleInterval",)
    configCycleInterval = 20  # minutes
    rrd = None
    shutdown = False
    thresholds = None

    def __init__(self, name, noopts=False):
        """
        Initializer

        @param name: name of the daemon
        @type name: string
        @param noopts: process command-line arguments?
        @type noopts: boolean
        """
        super(RRDDaemon, self).__init__(noopts, name=name)
        self.events = []
        self.thresholds = Thresholds()

    def getDevicePingIssues(self):
        """
        Determine which devices we shouldn't expect to hear back from.

        @return: list of devices
        @rtype: list
        """
        return self.eventService().callRemote("getDevicePingIssues")

    def remote_setPropertyItems(self, items):
        """
        Set zProperties provided from zenhub.

        @param items: list of zProperties to obtain
        @type items: list
        """
        self.log.debug("Async update of collection properties")
        self.setPropertyItems(items)

    def setPropertyItems(self, items):
        """
        Set zProperties

        @param items: list of zProperties
        @type items: list
        """
        table = dict(items)
        for name in self.properties:
            value = table.get(name, None)
            if value is not None:
                if getattr(self, name) != value:
                    self.log.debug("Updated %s config to %s", name, value)
                setattr(self, name, value)

    def sendThresholdEvent(self, **kw):
        """
        "Send the right event class for threshhold events"

        @param kw: keyword arguments describing an event
        @type kw: dictionary of keyword arguments
        """
        self.sendEvent({}, **kw)

    def buildOptions(self):
        """
        Command-line options to add
        """
        super(RRDDaemon, self).buildOptions()
        self.parser.add_option(
            "-d",
            "--device",
            dest="device",
            default="",
            help="Specify a device ID to monitor",
        )

    def logError(self, msg, error):
        """
        Log messages to the logger

        @param msg: the message
        @type msg: string
        @param error: an exception
        @type error: Exception
        """
        if isinstance(error, failure.Failure):
            from twisted.internet.error import TimeoutError

            if isinstance(error.value, TimeoutError):
                self.log.warning("Timeout Error")
            else:
                self.log.exception(error)
        else:
            self.log.error("%s %s", msg, error)

    def error(self, error):
        """
        Log an error, including any traceback data for a failure Exception
        Stop if we got the --cycle command-line option.

        @param error: the error message
        @type error: string
        """
        self.logError("Error", error)
        if not self.options.cycle:
            self.stop()

    def errorStop(self, why):
        """
        Twisted callback to receive fatal messages.

        @param why: the error message
        @type why: string
        """
        self.error(why)
        self.stop()

    def model(self):
        """
        Return the list of services from zenhub

        @return: list of services
        @rtype: list
        """
        return self.services.get(self.initialServices[-1], FakeRemote())
