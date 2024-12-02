##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.internet import protocol, reactor, defer, task
from twisted.internet.error import ConnectionClosed
from twisted.spread.pb import PBClientFactory

log = logging.getLogger("zen.pbclientfactory")

OPTION_STATE = 1
CONNECT_TIMEOUT = 60


class ReconnectingPBClientFactory(
    PBClientFactory, protocol.ReconnectingClientFactory
):
    maxDelay = 60

    def __init__(
        self,
        connectTimeout=30,
        pingPerspective=True,
        pingInterval=30,
        pingtimeout=120,
    ):
        PBClientFactory.__init__(self)
        self._creds = None
        self._scheduledConnectTimeout = None
        self._connectTimeout = connectTimeout
        # should the perspective be pinged. Perspective must have a ping
        # method. Deprecated => Always False.
        self._shouldPingPerspective = pingPerspective
        # how often to ping
        self._pingInterval = pingInterval
        # how long to wait for a ping before closing connection
        self._pingTimeoutTime = pingtimeout
        # ref to the scheduled ping timeout call
        self._pingTimeout = None
        # looping call doing the ping
        self._pingCheck = None
        self._perspective = None

    def connectTCP(self, host, port):
        factory = self
        self.connector = reactor.connectTCP(host, port, factory)
        setKeepAlive(self.connector.transport.socket)
        return self.connector

    def setCredentials(self, credentials):
        self._creds = credentials

    def _login(self, credentials, client=None):
        log.debug("_login called")
        d = PBClientFactory.login(self, credentials, client)
        d.addCallback(self._gotPerspective)
        d.addErrback(self.gotPerspectiveFailed)
        return d

    def clientConnectionFailed(self, connector, reason):
        log.debug("clientConnectionFailed %s", reason)
        self._perspective = None
        self._cancelConnectTimeout()
        PBClientFactory.clientConnectionFailed(self, connector, reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason
        )

    def clientConnectionLost(self, connector, reason):
        log.debug("clientConnectionLost %s", reason)
        self._perspective = None
        self._cancelConnectTimeout()
        PBClientFactory.clientConnectionLost(
            self, connector, reason, reconnecting=1
        )
        protocol.ReconnectingClientFactory.clientConnectionLost(
            self, connector, reason
        )

    def clientConnectionMade(self, broker):
        log.debug("clientConnectionMade")
        self.resetDelay()
        self._cancelConnectTimeout()
        PBClientFactory.clientConnectionMade(self, broker)
        if self._creds:
            self._startConnectTimeout("Login")
            self._login(self._creds)

    def startedConnecting(self, connector):
        log.debug("Starting connection...")
        self._startConnectTimeout("Initial connect")
        self.connecting()

    def connecting(self):
        """
        Called when a connection is about to be attempted. Can be the initial
        connect or a retry/reconnect
        """
        pass

    def gotPerspective(self, perspective):
        log.debug("gotPerspective")

    def gotPerspectiveFailed(self, reason):
        self._cancelConnectTimeout()
        if reason.type == "twisted.cred.error.UnauthorizedLogin":
            log.critical("zenhub username/password combination is incorrect!")
            # Don't exit as Enterprise caches info and can survive
        else:
            log.critical(
                "Unknown connection problem to zenhub %s", reason.type
            )

    def _gotPerspective(self, perspective):
        self._cancelConnectTimeout()
        self._cancelPingTimeout()
        self._perspective = perspective
        if self._shouldPingPerspective:
            reactor.callLater(0, self._startPingCycle)
        self.gotPerspective(perspective)

    def _disconnect(self):
        if self._broker:
            self.disconnect()
        elif self.connector:
            try:
                self.connector.disconnect()
            except Exception:
                log.exception("Could not disconnect")
        else:
            log.debug("No connector or broker to disconnect")

    # methods for connecting and login timeout
    def _startConnectTimeout(self, msg):
        self._cancelConnectTimeout()
        self._scheduledConnectTimeout = reactor.callLater(
            self._connectTimeout, self._timeoutConnect, msg
        )

    def _timeoutConnect(self, msg):
        log.info("%s timed out after %s seconds", msg, self._connectTimeout)
        self._disconnect()

    def _cancelConnectTimeout(self):
        self._scheduledConnectTimeout, timeout = (
            None,
            self._scheduledConnectTimeout,
        )
        if timeout and timeout.active():
            log.debug("Cancelling connect timeout")
            timeout.cancel()

    # methods to check connection is active
    def _startPingTimeout(self):
        if not self._pingTimeout:
            self._pingTimeout = reactor.callLater(
                self._pingTimeoutTime, self._doPingTimeout
            )

    def _cancelPingTimeout(self):
        self._pingTimeout, timeout = None, self._pingTimeout
        if timeout and timeout.active():
            log.debug("Cancelling ping timeout")
            timeout.cancel()

    def _doPingTimeout(self):
        if self._perspective:
            log.warn(
                "Perspective ping timed out after %s seconds",
                self._pingTimeoutTime,
            )
            self._disconnect()

    @defer.inlineCallbacks
    def _startPingCycle(self):
        if not self._pingCheck:
            pingCheck = task.LoopingCall(self._pingPerspective)
            self._pingCheck = pingCheck
            try:
                yield pingCheck.start(self._pingInterval)
            except Exception:
                log.exception("perspective ping loop died")
            finally:
                # should only happen at shutdown
                log.info("perspective ping loop ended")

    @defer.inlineCallbacks
    def _pingPerspective(self):
        try:
            if self._perspective:
                log.debug("pinging perspective")
                self._startPingTimeout()
                response = yield self._perspective.callRemote("ping")
                log.debug("perspective %sed", response)
            else:
                log.debug("skipping perspective ping")
            self._cancelPingTimeout()
        except ConnectionClosed:
            log.info("Connection was closed")
            self._cancelPingTimeout()
        except Exception:
            log.exception("ping perspective exception")


def setKeepAlive(sock):
    """Configure a socket for a longer keep-alive interval."""
    import socket

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE)
    sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT)
    interval = max(CONNECT_TIMEOUT / 4, 10)
    sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval)
    sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)
