##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""SshClient runs commands on a remote box using SSH and
returns their results.

See http://twistedmatrix.com/trac/wiki/Documentation for Twisted documentation,
specifically documentation on 'conch' (Twisted's SSH protocol support).
"""

import logging
import os
import pprint
import socket
import sys

from twisted.conch.ssh import (
    channel,
    common,
    connection,
    transport,
    userauth,
)
from twisted.conch.ssh.keys import Key
from twisted.internet import defer, reactor
from zope.component import queryUtility

from Products.DataCollector import CollectorClient
from Products.DataCollector.Exceptions import LoginFailed
from Products.ZenEvents import Event
from Products.ZenHub.interfaces import IEventService
from Products.ZenUtils.IpUtil import getHostByName
from Products.ZenUtils.Utils import getExitMessage

log = logging.getLogger("zen.SshClient")

# NB: Most messages returned back from Twisted are Unicode.
#     Expect to use str() to convert to ASCII before dumping out. :)


def sendEvent(
    self, message="", device="", severity=Event.Error, event_key=None
):
    """
    Shortcut version of sendEvent()

    @param message: message to send in Zenoss event
    @type message: string
    @param device: hostname of device to which this event is associated
    @type device: string
    @param severity: Zenoss severity from Products.ZenEvents
    @type severity: integer
    @param event_key: The event key to use for event clearing.
    @type event_key: string
    """

    # Parse out the daemon's name
    component = os.path.basename(sys.argv[0]).replace(".py", "")

    def hasattr_path(object_root, path):
        """
        The regular hasattr() only works on one component,
        not multiples.

        @param object_root: object to start searching for path
        @type object_root: object
        @param path: path to func or variable (eg "conn.factory" )
        @type path: string
        @return: is object_root.path sane?
        @rtype: boolean
        """

        obj = object_root
        for chunk in path.split("."):
            obj = getattr(obj, chunk, None)
            if obj is None:
                return False
        return True

    # ... and the device's name (as known by Zenoss)
    if device == "":
        if hasattr_path(self, "factory.hostname"):
            device = self.factory.hostname

        elif hasattr_path(self, "conn.factory.hostname"):
            device = self.conn.factory.hostname

        else:
            log.debug("Couldn't get the remote device's hostname")

    error_event = {
        "agent": component,
        "summary": message,
        "device": device,
        "eventClass": "/Cmd/Fail",
        "component": component,
        "severity": severity,
    }
    if event_key:
        error_event["eventKey"] = event_key

    event_service = queryUtility(IEventService)
    event_service.sendEvent(error_event)


class SshClientError(Exception):
    """
    Exception class
    """


class SshClientTransport(transport.SSHClientTransport):
    """
    Base client class for constructing Twisted Conch services.
    This class is *only* responsible for connecting to the SSH
    service on the device, and ensuring that *host* keys are sane.
    """

    def verifyHostKey(self, hostKey, fingerprint):
        """
        Verifies the host's SSH key against the stored fingerprint we have
        from the last time that we communicated with the host.

        NB: currently only trusts every host key without verification.

        @param hostKey: host's SSH key (unused)
        @type hostKey: string
        @param fingerprint: host fingerprint (unused)
        @type fingerprint: string
        @return: Twisted deferred object
        @rtype: Twisted deferred object (defer.succeed(1)
        @todo: verify the host key
        """
        # blowing off host key right now, should store and check
        from Products.ZenUtils.Utils import unused

        unused(hostKey)
        log.debug(
            "%s host fingerprint: %s",
            self.factory.hostname,
            fingerprint,
        )
        return defer.succeed(1)

    def connectionMade(self):
        """
        Called after the connection has been made.
        Used to set up private instance variables.
        """
        self.factory.transport = self.transport
        transport.SSHClientTransport.connectionMade(self)

    def receiveError(self, reasonCode, description):
        """
        Called when a disconnect error message was received from the device.

        @param reasonCode: error code from SSH connection failure
        @type reasonCode: integer
        @param description: human-readable version of the error code
        @type description: string
        """
        message = "SSH error from remote device (code %d): %s\n" % (
            reasonCode,
            str(description),
        )
        log.warn(message)
        sendEvent(self, message=message)
        transport.SSHClientTransport.receiveError(
            self, reasonCode, description
        )

    def receiveUnimplemented(self, seqnum):
        """
        Called when an unimplemented packet message was received
        from the device.

        @param seqnum: SSH message code
        @type seqnum: integer
        """
        message = "Got 'unimplemented' SSH message, seqnum= %d" % seqnum
        log.info(message)
        sendEvent(self, message=message)
        transport.SSHClientTransport.receiveUnimplemented(self, seqnum)

    def receiveDebug(self, alwaysDisplay, message, lang):
        """
        Called when a debug message was received from the device.

        @param alwaysDisplay: boolean-type code to indicate if the
            message is to be displayed
        @type alwaysDisplay: integer
        @param message: debug message from remote device
        @type message: string
        @param lang: language code
        @type lang: integer
        """
        message = "Debug message from remote device (%s): %s" % (
            lang,
            message,
        )
        log.info(message)
        sendEvent(self, message=message, severity=Event.Debug)

        transport.SSHClientTransport.receiveDebug(
            self, alwaysDisplay, message, lang
        )

    def connectionSecure(self):
        """
        Called after the connection is set up and other services can be run.
        This function starts the SshUserAuth client (ie the Connection client).
        """
        sshconn = SshConnection(self.factory)
        sshauth = SshUserAuth(self.factory.username, sshconn, self.factory)
        self.requestService(sshauth)


class NoPasswordException(Exception):
    pass


class SshUserAuth(userauth.SSHUserAuthClient):
    """
    Class to gather credentials for use with our SSH connection,
    and use them to authenticate against the remote device.
    """

    def __init__(self, user, instance, factory):
        """
        If no username is supplied, defaults to the user running this code
        (eg zenoss)

        @param user: username
        @type user: string
        @param instance: instance object
        @type instance: object
        @param factory: factory info
        @type factory: Twisted factory object
        """

        user = str(user)  # damn unicode
        if user == "":
            log.debug(
                "Unable to determine username/password from "
                "zCommandUser/zCommandPassword"
            )

            # From the Python docs about the preferred method of
            # obtaining user name in preference to os.getlogin()
            #  (http://docs.python.org/library/os.html)
            import pwd

            try:
                user = os.environ.get("LOGNAME", pwd.getpwuid(os.getuid())[0])
            except Exception:
                pass

            if user == "":
                message = (
                    "No zProperties defined and unable to determine "
                    "current user."
                )
                log.error(message)
                sendEvent(self, message=message)
                raise SshClientError(message)

        userauth.SSHUserAuthClient.__init__(self, user, instance)
        self._sent_password = False
        self._sent_pk = False
        self._sent_kbint = False
        self._auth_failures = []
        self._auth_succeeded = False
        self.user = user
        self.factory = factory
        self._key = self._getKey()

    def getPassword(self, unused=None):
        """
        Called from conch.

        Return a deferred object of success if there's a password or
        return fail (ie no zCommandPassword specified)

        @param unused: unused (unused)
        @type unused: string
        @return: Twisted deferred object (defer.succeed or defer.fail)
        @rtype: Twisted deferred object
        """
        # Don't re-send the same credentials if we have already been called
        if self._sent_password:
            return None
        try:
            password = self._getPassword()
            d = defer.succeed(password)
            self._sent_password = True
        except NoPasswordException:
            # NOTE: Return None here - not a defer.fail().  If a failure
            # deferred is returned, then the SSH client will retry until
            # MaxAuthTries is met - which in some SSH server implementations
            # means an infinite number of retries.  Returning None here
            # indicates that we don't want to try password authentication
            # because we don't have a username or password.
            d = None
        return d

    def getGenericAnswers(self, name, instruction, prompts):
        """
        Called from conch.

        Returns a L{Deferred} with the responses to the prompts.

        @param name: The name of the authentication currently in progress.
        @param instruction: Describes what the authentication wants.
        @param prompts: A list of (prompt, echo) pairs, where prompt is a
        string to display and echo is a boolean indicating whether the
        user's response should be echoed as they type it.
        """
        log.debug(
            'getGenericAnswers name="%s" instruction="%s" prompts=%s',
            name,
            instruction,
            pprint.pformat(prompts),
        )
        if not prompts:
            # RFC 4256 - In the case that the server sends a `0' num-prompts
            # field in the request message, the client MUST send a response
            # message with a `0' num-responses field to complete the exchange.
            d = defer.succeed([])
        else:
            responses = []
            found_prompt = False
            for prompt, echo in prompts:
                if "password" in prompt.lower():
                    found_prompt = True
                    try:
                        responses.append(self._getPassword())
                    except NoPasswordException:
                        # This shouldn't happen - we don't support keyboard
                        # interactive auth unless a password is specified.
                        log.debug(
                            "getGenericAnswers called with empty password"
                        )
            if not found_prompt:
                log.warning("No known prompts: %s", pprint.pformat(prompts))
            d = defer.succeed(responses)
        return d

    def _getPassword(self):
        """
        Get the password. Raise an exception if it is not set.
        """
        if not self.factory.password:
            message = (
                "SshUserAuth: no password found -- "
                + "has zCommandPassword been set?"
            )
            raise NoPasswordException(message)
        return self.factory.password

    def _handleFailure(self, message, event_key=None):
        """
        Handle a failure by logging a message and sending an event.
        """
        log.error(message)
        sendEvent(self, message=message, event_key=event_key)

    def _handleLoginSuccess(self, message, event_key=None):
        """
        Handle SSH login success by clearing any failure events.
        """
        sendEvent(
            self, message=message, event_key=event_key, severity=Event.Clear
        )

    def _getKey(self):
        keyPath = os.path.expanduser(self.factory.keyPath)
        log.debug(
            "Expanded SSH key path from zKeyPath %s to %s",
            self.factory.keyPath,
            keyPath,
        )
        key = None
        if os.path.exists(keyPath):
            try:
                data = "".join(open(keyPath).readlines()).strip()
                key = Key.fromString(data, passphrase=self.factory.password)
            except IOError as ex:
                message = "Unable to read the SSH key file because %s" % ex
                log.warn(message)
                device = "localhost"  # Fallback
                try:
                    device = socket.getfqdn()
                except Exception:
                    pass
                sendEvent(
                    self,
                    device=device,
                    message=message,
                    severity=Event.Warning,
                )
        else:
            log.debug("SSH key path %s doesn't exist", keyPath)
        return key

    def getPublicKey(self):
        """
        Return the SSH public key (using the zProperty zKeyPath) or None

        @return: SSH public key
        @rtype: string
        """
        # Don't re-send the same public key if we have already been called.
        # TODO: Would be good to expand to support sending multiple keys.
        if self._key is not None and not self._sent_pk:
            self._sent_pk = True
            return self._key

    def getPrivateKey(self):
        """
        Return a deferred with the SSH private key
        (using the zProperty zKeyPath)

        @return: Twisted deferred object (defer.succeed)
        @rtype: Twisted deferred object
        """
        return defer.succeed(self._key)

    def auth_keyboard_interactive(self, *args, **kwargs):
        # Don't authenticate multiple times with same credentials
        if self._sent_kbint:
            return False
        # Only return that we support keyboard-interactive authentication if a
        # password is specified.
        try:
            self._getPassword()
            self._sent_kbint = True
            return userauth.SSHUserAuthClient.auth_keyboard_interactive(
                self, *args, **kwargs
            )
        except NoPasswordException:
            return False

    def ssh_USERAUTH_FAILURE(self, *args, **kwargs):
        if (
            self.lastAuth != "none"
            and self.lastAuth not in self._auth_failures
        ):
            self._auth_failures.append(self.lastAuth)
        return userauth.SSHUserAuthClient.ssh_USERAUTH_FAILURE(
            self, *args, **kwargs
        )

    def ssh_USERAUTH_SUCCESS(self, *args, **kwargs):
        self._auth_succeeded = True
        return userauth.SSHUserAuthClient.ssh_USERAUTH_SUCCESS(
            self, *args, **kwargs
        )

    def serviceStopped(self, *args, **kwargs):
        # Notify that the client has finished - authentication has failed.
        if not self._auth_succeeded:
            # If we sent some type of authentication,
            # log an error and send an event.
            if self._auth_failures:
                log.debug(
                    "Authentication failed for auth type(s): %s",
                    ",".join(self._auth_failures),
                )
                msg = "SSH login to %s with username %s failed" % (
                    self.factory.hostname,
                    self.user,
                )
            else:
                msg = (
                    "SSH authentication failed - "
                    "no password or public key specified"
                )
            self._handleFailure(msg, event_key="sshClientAuth")
            self.factory.clientFinished(LoginFailed(msg))
        else:
            msg = "SSH Authentication succeeded for username %s" % self.user
            sendEvent(
                self, msg, severity=Event.Clear, event_key="sshClientAuth"
            )
            self._handleLoginSuccess(msg, event_key="sshClientAuth")
        return userauth.SSHUserAuthClient.serviceStopped(self, *args, **kwargs)


class SshConnection(connection.SSHConnection):
    """
    Wrapper class that starts channels on top of connections.
    """

    def __init__(self, factory):
        """
        Initializer

        @param factory: factory containing the connection info
        @type factory: Twisted factory object
        """
        log.debug("Creating new SSH connection...")
        connection.SSHConnection.__init__(self)
        self.factory = factory

    def ssh_CHANNEL_FAILURE(self, packet):
        """
        Called when the SSH session can't authenticate

        @param packet: returned packet from the host
        @type packet: object
        """
        message = "CHANNEL_FAILURE: Authentication failure"
        log.error(message)
        sendEvent(self, message=message)
        connection.SSHConnection.ssh_CHANNEL_FAILURE(self, packet)

    def ssh_CHANNEL_OPEN_FAILURE(self, packet):
        """
        Called when the SSH session can't authenticate

        @param packet: returned packet from the host
        @type packet: object
        """
        message = "CHANNEL_OPEN_FAILURE: Try lowering zSshConcurrentSessions"
        log.error(message)
        sendEvent(self, message=message)
        connection.SSHConnection.ssh_CHANNEL_OPEN_FAILURE(self, packet)

    def ssh_REQUEST_FAILURE(self, packet):
        """
        Called when the SSH session can't authenticate

        @param packet: returned packet from the host
        """
        message = "REQUEST_FAILURE: Authentication failure"
        log.error(message)
        sendEvent(self, message=message)
        connection.SSHConnection.ssh_REQUEST_FAILURE(self, packet)

    def openFailed(self, reason):
        """
        Called when the connection open() fails.
        Usually this gets called after too many bad connection attempts,
        and the remote device gets upset with us.

        NB: reason.desc is the human-readable description of the failure
            reason.code is the SSH error code (see
            http://tools.ietf.org/html/rfc4250#section-4.2.2 for more details)

        @param reason: reason object
        @type reason: reason object
        """
        message = "SSH connection to %s failed (error code %d): %s" % (
            self.command,
            reason.code,
            reason.desc,
        )
        log.error(message)
        sendEvent(self, message=message)
        connection.SSHConnection.openFailed(self, reason)

    def serviceStarted(self):
        """
        Called when the service is active on the transport
        """
        self.factory.serviceStarted(self)

    def addCommand(self, cmd):
        """
        Open a new channel for each command in queue

        @param cmd: command to run
        @type cmd: string
        """
        ch = CommandChannel(cmd, conn=self)
        self.openChannel(ch)
        targetIp = self.transport.transport.addr[0]
        log.debug(
            "%s channel %s SshConnection added command %s",
            targetIp,
            ch.id,
            cmd,
        )

    def channelClosed(self, channel):
        """
        Called when a channel is closed.
        REQUIRED function by Twisted.

        @param channel: channel that closed
        @type channel: Twisted channel object
        """
        targetIp = self.transport.transport.addr[0]
        log.debug("%s channel %s SshConnection closing", targetIp, channel.id)
        # grr.. patch SSH inherited method to deal with partially
        # configured channels
        self.localToRemoteChannel[channel.id] = None
        self.channelsToRemoteChannel[channel] = None
        connection.SSHConnection.channelClosed(self, channel)


class CommandChannel(channel.SSHChannel):
    """
    The class that actually interfaces between Zenoss and the device.
    """

    name = "session"
    conn = None

    def __init__(self, command, conn=None):
        """
        Initializer

        @param command: command to run
        @type command: string
        @param conn: connection to create the channel on
        @type conn: Twisted connection object
        """
        channel.SSHChannel.__init__(self, conn=conn)
        self.command = command
        self.exitCode = None
        self.stderr = None

    @property
    def targetIp(self):
        if self.conn:
            return self.conn.transport.transport.addr[0]

    def openFailed(self, reason):
        """
        Called when the open fails.
        """
        from twisted.conch.error import ConchError

        if isinstance(reason, ConchError):
            args = (reason.data, reason.value)
        else:
            args = (reason.code, reason.desc)
        message = "CommandChannel Open of %s failed (error code %d): %s" % (
            (self.command,) + args
        )
        log.warn("%s %s", self.targetIp, message)
        sendEvent(self, message=message)
        channel.SSHChannel.openFailed(self, reason)
        if self.conn is not None:
            self.conn.factory.clientFinished()

    def extReceived(self, dataType, data):
        """
        Called when we receive extended data (usually standard error)

        @param dataType: data type code
        @type dataType: integer
        """
        message = (
            "The command %s returned stderr data (%d) from the device: %r"
            % (self.command, dataType, data)
        )
        log.warn("%s channel %s %s", self.targetIp, self.id, message)
        sendEvent(self, message=message)
        self.stderr += data

    @defer.inlineCallbacks
    def channelOpen(self, unused):
        """
        Initialize the channel and send our command to the device.

        @param unused: unused (unused)
        @type unused: string
        @return: Twisted channel
        @rtype: Twisted channel
        """

        log.debug(
            "%s channel %s Opening command channel for %s",
            self.targetIp,
            self.id,
            self.command,
        )
        self.data = ""
        self.stderr = ""

        #  Notes for sendRequest:
        # 'exec'      - execute the following command and exit
        # common.NS() - encodes the command as a length-prefixed string
        # wantReply   - reply to let us know the process has been started
        try:
            result = yield self.conn.sendRequest(
                self, "exec", common.NS(self.command), wantReply=1
            )
        except Exception as e:
            log.warn(
                "%s channel %s failed during command execution with error: %s",
                self.targetIp,
                self.id,
                e,
            )
            defer.returnValue([])
        defer.returnValue(result)

    def request_exit_status(self, data):
        """
        Gathers the exit code from the device

        @param data: returned value from device
        @type data: packet
        """
        import struct

        self.exitCode = struct.unpack(">L", data)[0]
        log.debug(
            "%s channel %s CommandChannel exit code for %s is %d: %s",
            self.targetIp,
            self.id,
            self.command,
            self.exitCode,
            getExitMessage(self.exitCode),
        )

    def dataReceived(self, data):
        """
        Response stream from the device.  Can be called multiple times.

        @param data: returned value from device
        @type data: string
        """
        self.data += data

    def closed(self):
        """
        Cleanup for the channel, as both ends have closed the channel.
        """
        log.debug(
            "%s channel %s CommandChannel closing command channel for "
            "command %s with data: %r",
            self.targetIp,
            self.id,
            self.command,
            self.data,
        )
        self.conn.factory.addResult(
            self.command, self.data, self.exitCode, self.stderr
        )
        self.loseConnection()

        self.conn.factory.channelClosed()


class SshClient(CollectorClient.CollectorClient):
    """
    SSH Collector class to connect to a particular device
    """

    def __init__(
        self,
        hostname,
        ip,
        port=22,
        plugins=[],
        options=None,
        device=None,
        datacollector=None,
        isLoseConnection=False,
    ):
        """
        Initializer

        @param hostname: hostname of the device
        @type hostname: string
        @param ip: IP address of the device
        @type ip: string
        @param port: port number to use to connect to device
        @type port: integer
        @param plugins: plugins
        @type plugins: list of plugins
        @param options: options
        @type options: list
        @param device: name of device
        @type device: string
        @param datacollector: object
        @type datacollector: object
        """

        CollectorClient.CollectorClient.__init__(
            self, hostname, ip, port, plugins, options, device, datacollector
        )
        self.hostname = hostname
        self.protocol = SshClientTransport
        self.connection = None
        self.transport = None
        self.openSessions = 0
        self.workList = list(self.getCommands())
        self.isLoseConnection = isLoseConnection

    def run(self):
        """
        Start SSH collection.
        """
        log.debug(
            "%s SshClient connecting to %s:%s with timeout %s seconds",
            self.ip,
            self.hostname,
            self.port,
            self.loginTimeout,
        )
        reactor.connectTCP(self.ip, self.port, self, self.loginTimeout)

    def runCommands(self):
        log.debug(
            "%s SshClient has %d commands to assign to channels "
            "(max = %s, current = %s)",
            self.ip,
            len(self.workList),
            self.concurrentSessions,
            self.openSessions,
        )
        availSessions = self.concurrentSessions - self.openSessions
        for i in range(min(len(self.workList), availSessions)):
            cmd = self.workList.pop(0)
            self.openSessions += 1
            self.connection.addCommand(cmd)

    def channelClosed(self):
        self.openSessions -= 1
        log.debug(
            "%s SshClient closing channel (openSessions = %s)",
            self.ip,
            self.openSessions,
        )
        if self.commandsFinished():
            if self.isLoseConnection:
                self.transport.loseConnection()
            self.clientFinished()
            return

        if self.workList:
            cmd = self.workList.pop(0)
            self.openSessions += 1
            if self.connection:
                self.connection.addCommand(cmd)

    def serviceStarted(self, sshconn):
        """
        Run commands that are in the command queue

        @param sshconn: connection to create channels on
        @type sshconn: Twisted SSH connection
        """
        log.debug(
            "SshClient connected to device %s (%s)", self.hostname, self.ip
        )
        self.connection = sshconn
        self.runCommands()

    def addCommand(self, commands):
        """
        Add a command or commands to queue and open a command
        channel for each command

        @param commands: commands to run
        @type commands: list
        """
        CollectorClient.CollectorClient.addCommand(self, commands)
        if isinstance(commands, basestring):
            commands = (commands,)
        self.workList.extend(commands)

        # This code is required when we're reused by zencommand.
        if self.connection:
            self.runCommands()

    def clientConnectionFailed(self, connector, reason):
        """
        If we didn't connect let the modeler know

        @param connector: connector associated with this failure
        @type connector: object
        @param reason: failure object
        @type reason: object
        """
        from Products.ZenUtils.Utils import unused

        unused(connector)
        message = reason.getErrorMessage()
        log.error("%s %s", self.ip, message)
        sendEvent(self, device=self.hostname, message=message)
        self.clientFinished()

    def loseConnection(self):
        """
        Called when the connection gets closed.
        """
        log.debug("%s SshClient connection closed", self.ip)
        # self.connection.loseConnection()


def main():
    """
    Test harness main()

    Usage:

    python SshClient.py hostname[:port] comand [command]

    Each command must be enclosed in quotes (") to be interpreted
    properly as a complete unit.
    """
    logging.basicConfig()

    parser = CollectorClient.buildOptions()
    options = CollectorClient.parseOptions(parser, 22)
    log.setLevel(options.logseverity)

    client = SshClient(
        options.hostname,
        getHostByName(options.hostname),
        options.port,
        options=options,
    )

    # Rather than getting info from zenhub, just pass our
    # commands in
    client.workList = options.commands

    client.run()

    client.clientFinished = reactor.stop
    client._commands.append(options.commands)
    reactor.run()

    pprint.pprint(client.getResults())


if __name__ == "__main__":
    main()
