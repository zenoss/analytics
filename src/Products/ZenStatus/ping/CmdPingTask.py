##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""CmdPingTask

Determines the availability of a IP addresses using command line ping.

"""

import logging
import time

from twisted.internet import defer, utils
from zope import interface

from Products import ZenStatus
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenUtils.Utils import unused

from .PingResult import PingResult

unused(DeviceProxy)

log = logging.getLogger("zen.zenping.cmdping")

_PING = None
_PING6 = None
_PING_ARG_TEMPLATE = None
_OK = 0


def _detectPing():
    import subprocess

    global _PING, _PING6, _PING_ARG_TEMPLATE
    try:
        _PING = subprocess.check_output(["which", "ping"]).strip()
    except subprocess.CalledProcessError:
        log.error("no command line ping detected")
        import sys

        sys.exit(1)
    try:
        _PING6 = subprocess.check_output(["which", "ping6"]).strip()
    except subprocess.CalledProcessError:
        log.info("ping6 not found in path")

    _PING_ARG_TEMPLATE = (
        "%(ping)s -n -s %(datalength)d -c 1 -t %(ttl)d -w %(timeout)d %(ip)s"
    )
    import platform

    system = platform.system()
    if system in ("Mac OS X", "Darwin"):
        log.info("Mac OS X detected; adjusting ping args.")
        _PING_ARG_TEMPLATE = (
            "%(ping)s -n -s %(datalength)d -c 1 "
            "-m %(ttl)d -t %(timeout)d %(ip)s"
        )
    elif system != "Linux":
        log.info(
            "CmdPing has not been tested on %r; assuming that Linux "
            "ping args work."
        )


_detectPing()


def _getPingCmd(version=6, **kwargs):
    args = kwargs.copy()
    if version == 6:
        args["ping"] = _PING6
    else:
        args["ping"] = _PING

    cmd_str = _PING_ARG_TEMPLATE % args
    cmd_list = cmd_str.split(" ")
    return (cmd_list[0], cmd_list[1:])


class CmdPingCollectionPreferences(ZenStatus.PingCollectionPreferences):
    """
    This required to be a ping backend; use default implementation.
    """


@interface.implementer(ZenStatus.interfaces.IPingTaskFactory)
class CmdPingTaskFactory(object):
    """
    A Factory to create command line PingTasks.
    """

    def __init__(self):
        self.reset()

    def build(self):
        task = CmdPingTask(
            self.name,
            self.configId,
            self.interval,
            self.config,
        )
        return task

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None


@interface.implementer(ZenStatus.interfaces.IPingTask)
class CmdPingTask(ZenStatus.PingTask):
    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to ping the device and any of its interfaces.
        @rtype: Twisted deferred object
        """
        self.resetPingResult()
        return self._pingIp()

    @defer.inlineCallbacks
    def _pingIp(self):
        maxTries = self.config.tries
        attempts = 0
        exitCode = -1
        timestamp = None
        while attempts < maxTries:
            attempts += 1
            # we need to increase the packet size to atleast 16 because 64bit
            # version of ping does not return RTT data if packet length is
            # < 16.  This is from
            # :http://www.linuxcommand.org/man_pages/ping8.html: 'If the data
            # space is at least of size of struct timeval ping  uses the
            # beginning  bytes  of this space to include a timestamp which it
            # uses in the computation of round trip times.  If the data space
            # is shorter,  no round trip times are given.' Timeval is 16 bytes
            # long on x86-64 and 8 bytes long on x86.
            cmd, args = _getPingCmd(
                ip=self.config.ip,
                version=self.config.ipVersion,
                ttl=64,
                timeout=int(self._preferences.pingTimeOut),
                datalength=self._daemon.options.dataLength
                if self._daemon.options.dataLength > 16
                else 16,
            )
            log.debug("%s %s", cmd, " ".join(args))
            timestamp = time.time()
            out, err, exitCode = yield utils.getProcessOutputAndValue(
                cmd, args
            )
            pingResult = PingResult(self.config.ip, exitCode, out, timestamp)
            self.logPingResult(pingResult)
            if not self.config.points and exitCode == 0:
                # if there are no datapoints to store
                # and there is at least 1 ping up, then go on
                break

        if self.isUp:
            log.debug("%s is up!", self.config.ip)
            self.sendPingUp()
        else:
            log.debug("%s is down", self.config.ip)
            self.sendPingDown()
        self.storeResults()
