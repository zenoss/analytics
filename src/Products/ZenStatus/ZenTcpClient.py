##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ZenTcpClient
Connect to the remote service and (optionally) test the output from
the service against what we expect.

Error types:

    1. timeout (no connection)
    2. connection refused - port not available on remote end
    3. bad value - value returned did not match expectRegex

"""

import logging
import re
import socket  # So we can refer to the exception socket.error

from socket import getfqdn, SOL_SOCKET, SO_LINGER
from struct import pack

from twisted.internet import reactor, protocol, defer

from Products.ZenEvents.ZenEventClasses import Status_IpService
from Products.ZenUtils.Utils import unused

log = logging.getLogger("zen.ZenTcpClient")
hostname = getfqdn()


class ZenTcpTest(protocol.Protocol):
    """
    Twisted class to make a TCP/IP connection to a remote IP service
    and report back the result.
    """

    defer = None
    data = ""

    def connectionMade(self):
        """
        Connected successfully to the remote device, now test against any
        regex that we might have and record the result.
        """
        log.debug("Connected to %s", self.transport.getPeer().host)
        self.factory.msg = "pass"
        self.cfg = self.factory.cfg

        if self.cfg.sendString:
            sendString = self.cfg.sendString.decode("string_escape")
            log.debug("Sending: %s", sendString)
            self.transport.write(sendString)

        if self.cfg.expectRegex:
            log.debug(
                "Waiting for results to check against regex '%s'",
                self.cfg.expectRegex,
            )
            self.defer = reactor.callLater(
                self.cfg.timeout, self.expectTimeout
            )
        else:
            self.loseConnection()

    def dataReceived(self, data):
        """
        Compare the data from the remote device to what we expect in the
        regex.

        @parameter data: output from remote service
        @type data: string
        """
        log.debug(
            "%s %s received data: %s",
            self.cfg.device,
            self.cfg.component,
            data,
        )
        self.data += data
        if self.cfg.expectRegex:
            if re.search(self.cfg.expectRegex, data):
                log.debug(
                    "Found %s in '%s' -- closing connection",
                    self.cfg.expectRegex,
                    data,
                )
                self.loseConnection()
            else:
                log.debug(
                    "No match for %s in '%s' -- looking for more data",
                    self.cfg.expectRegex,
                    data,
                )

    def expectTimeout(self):
        """
        Called if we timeout waiting for the service to connect or for
        receiving a response from the service that matches our regex.
        """
        msg = "IP Service %s TIMEOUT waiting for '%s'" % (
            self.cfg.component,
            self.cfg.expectRegex,
        )
        log.debug("%s %s", self.cfg.ip, msg)
        self.factory.msg = msg
        self.loseConnection()

    def loseConnection(self):
        """
        Shut down the connection and cleanup.
        """
        ip, port = self.transport.addr
        log.debug(
            "Closed connection to %s on port %s for %s",
            ip,
            port,
            self.cfg.component,
        )
        self.data = ""
        try:
            self.defer.cancel()
        except Exception:
            self.defer = None
        self.transport.loseConnection()


class ZenTcpClient(protocol.ClientFactory):
    """
    Client class to run TCP tests.
    """

    protocol = ZenTcpTest
    msg = "pass"
    deferred = None

    def __init__(self, svc, status):
        self.cfg = svc
        self.status = status

    def clientConnectionLost(self, connector, reason):
        """
        Record why the connection to the remote device was dropped.

        @parameter connector: Twisted protocol object
        @type connector: Twisted protocol object
        @parameter reason: explanation for the connection loss
        @type reason: Twisted error object
        """
        unused(connector)
        errorMsg = reason.getErrorMessage()
        if errorMsg != "Connection was closed cleanly.":
            log.debug(
                "Lost connection to %s (%s) port %s: %s",
                self.cfg.device,
                self.cfg.ip,
                self.cfg.port,
                reason.getErrorMessage(),
            )
        if self.deferred:
            self.deferred.callback(self)
        self.deferred = None

    def clientConnectionFailed(self, connector, reason):
        """
        Record why the connection to the remote device failed.

        @parameter connector: Twisted protocol object
        @type connector: Twisted protocol object
        @parameter reason: explanation for the connection loss
        @type reason: Twisted error object
        """
        log.debug(
            "Connection to %s (%s) port %s failed: %s",
            self.cfg.device,
            connector.host,
            self.cfg.port,
            reason.getErrorMessage(),
        )
        self.msg = "IP Service %s is down" % self.cfg.component
        if self.deferred:
            self.deferred.callback(self)
        self.deferred = None

    def getEvent(self):
        """
        Called by zenstatus to report status information about a service.

        @return: event of what happened to our service test
        @rtype: dictionary
        """
        if self.msg == "pass" and self.status > 0:
            self.status = sev = 0
            self.msg = "IP Service %s back up" % self.cfg.component

        elif self.msg != "pass":
            self.status += 1
            sev = self.cfg.failSeverity

        else:
            # Send an event even though there's no problem and
            # nothing to clear __internally__ to zenstatus.
            # The event console might have an event that will
            # otherwise never be cleared.
            # Code higher up discards duplicate clears.
            self.status = sev = 0
            self.msg = "IP Service %s back up" % self.cfg.component

        return dict(
            device=self.cfg.device,
            component=self.cfg.component,
            ipAddress=self.cfg.ip,
            summary=self.msg,
            severity=sev,
            eventClass=Status_IpService,
            eventGroup="TCPTest",
            agent="ZenStatus",
            manager=hostname,
        )

    def start(self, ip_address):
        """
        Called by zenstatus to make a connection attempt to the service.

        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        d = self.deferred = defer.Deferred()
        connector = reactor.connectTCP(
            ip_address, self.cfg.port, self, self.cfg.timeout
        )
        self.setNoLinger(connector)
        return d

    def setNoLinger(self, connector):
        """
        Stop zenstatus from leaving large numbers of sockets in TIME-WAIT
        state.

        The TIME-WAIT state is a TCP/IP sanity check to ensure that a packet
        that arrives from the network AFTER the connection is closed doesn't
        result in more error-handling communication between the devices.
        This is almost always a good thing.

        zenstatus does not perform long-running protocol-specific checks
        (ie usually just does socket open() + close()), so the TIME-WAIT
        sanity checks just pile up on the system, consuming kernel resources.

        Setting the LINGER socket option to *not* wait means that
        closed connections immediately discard the socket state AND
        send a TCP/IP RST ('reset') packet to the other device.
        This will result in "Connection reset by peer" messages on the
        remote device.
        """
        OPTION_STATE = 1  # on
        LINGER = 0  # Wait 0 seconds after closing the socket
        VALUES_STRUCT = pack("ii", OPTION_STATE, LINGER)
        try:
            connector.transport.socket.setsockopt(
                SOL_SOCKET, SO_LINGER, VALUES_STRUCT
            )
        except socket.error as ex:
            log.warn("Unable to set SO_LINGER on socket because: %s", ex)
