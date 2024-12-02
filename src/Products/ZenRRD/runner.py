##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from twisted.internet import reactor, defer
from twisted.internet.error import ProcessExitedAlready
from twisted.internet.protocol import ProcessProtocol
from twisted.python.failure import Failure

from zope.interface import Interface, Attribute, implementer

from Products.DataCollector.SshClient import SshClient
from Products.ZenCollector.pools import getPool
from Products.ZenUtils.Utils import DictAsObj

log = logging.getLogger("zen.runner")


class TimeoutError(Exception):
    def __init__(self, *args):
        super(TimeoutError, self).__init__()
        self.args = args


def getRunner(proxy=None, client=None, connection=None):
    # 'proxy' is a device config object.
    if client and issubclass(client, SshRunner.client):
        runner = SshRunner(proxy, client)
        runner.connection = connection
    else:
        runner = ProcessRunner(proxy)
    return runner


class IRunner(Interface):

    connection = Attribute("Object describing the client connection")
    client = Attribute("Client connection class")
    proxy = Attribute("Connection information about a device")
    exitCode = Attribute("The resulting exitcode from the given command")
    output = Attribute("Result of standard out")
    stderr = Attribute("Result of standard error")

    def connect(self, task):
        """
        Establishes a connection through the connection client.
        """

    def send(self, command):
        """
        Send a command through the connection.
        """

    def close(self):
        """
        Closes the connection to the client.
        """


class IClient(Interface):
    """
    Interface for supporting client connection objects
    """

    connect_defer = Attribute("Deferred for establishing a connection")
    command_defers = Attribute("Deferreds for submitting commands")
    close_defer = Attribute("Deferred for a closed connection")
    description = Attribute("String describing connection information")
    tasks = Attribute("Set of tasks associated with a connection")
    is_expired = Attribute("Boolean to mark an expired connection")


@implementer(IRunner)
class ProcessRunner(ProcessProtocol):
    """A ProcessRunner executes commands on the host (local server)."""

    connection = None
    client = None
    proxy = None
    exitCode = None
    output = None
    stderr = None

    def __init__(self, proxy):
        self.output = []
        self.stderr = []
        self.proxy = proxy

    def connect(self, task=None):
        log.debug("Running command(s) locally")
        return defer.succeed(None)

    def send(self, datasource):
        """
        Kick off the process

        @type datasource: Products.ZenRRD.zencommand.Cmd
        """
        log.debug("Running %s", datasource.command.split()[0])
        shell = "/bin/sh"
        cmdline = (shell, "-c", "exec %s" % datasource.command)

        self.datasource = datasource
        self.stdin = " ".join(cmdline)

        commandTimeout = self.proxy.zCommandCommandTimeout
        self._deferred = defer.Deferred()
        reactor.spawnProcess(self, shell, cmdline, env=datasource.env)
        self._timer = reactor.callLater(commandTimeout, self.timeout)
        self.isTimeout = False

        return self._deferred

    def close(self, *args):
        pass

    def timeout(self, timedOut=True):
        """
        Kill a process gracefully if it takes too long
        """
        self.isTimeout = True
        if not self._deferred.called:
            if timedOut:
                self._deferred.errback(TimeoutError(self.datasource))
            try:
                self.transport.signalProcess("INT")
                reactor.callLater(2, self._reap)
            except ProcessExitedAlready:
                log.debug("Command already exited: %s", self.stdin.split()[0])

    def _reap(self):
        """
        Kill a process forcefully if it takes too long
        """
        try:
            self.transport.signalProcess("KILL")
        except Exception:
            pass

    def outReceived(self, data):
        """
        Stores the result of stdout as it arrives from the process
        """
        self.output.append(data)

    def errReceived(self, data):
        """
        Stored the result of stderr as it arrives from the process
        """
        self.stderr.append(data)

    def processEnded(self, reason):
        """
        Notify the started that the process is complete
        """
        self.exitCode = reason.value.exitCode
        if self.exitCode is not None:
            if not self.isTimeout:
                self._timer.cancel()
            self.output = "".join(self.output)
            self.stderr = "".join(self.stderr)

            msg = "Datasource: %s Received exit code: %s Output: \n%r"
            data = [self.datasource.ds, self.exitCode, self.output]
            if self.stderr:
                msg += "\nStandard Error:\n%r"
                data.append(self.stderr)
            log.debug(msg, *data)

        d, self._deferred = self._deferred, None
        if not d.called:
            d.callback(self)


@implementer(IRunner)
class SshRunner(object):
    """Execute commands on the remote end of an SSH connection."""

    POOLNAME = "SSH Connections"
    EXPIRED_MESSAGES = (
        "WARNING: Your password has expired.\n"
        "Password change required but no TTY available.\n",
    )

    datasource = None
    connection = None
    client = SshClient
    proxy = None
    exitCode = None
    output = ""
    stderr = ""

    def __init__(self, proxy, client):
        self.proxy = proxy
        # NOTE: SshRunner only works with MySshClient from zencommand because
        # of its `is_expired` and `close_defer` attributes and its run method
        # which returns a deferred object.
        self.client = client

        self.task = None
        self.deviceId = self.proxy.id
        self.manageIp = self.proxy.manageIp
        self.port = self.proxy.zCommandPort

        _username = self.proxy.zCommandUsername or ""
        _password = self.proxy.zCommandPassword or ""
        _loginTimeout = self.proxy.zCommandLoginTimeout
        _commandTimeout = self.proxy.zCommandCommandTimeout
        _keyPath = self.proxy.zKeyPath
        _concurrentSessions = self.proxy.zSshConcurrentSessions

        self._sshOptions = DictAsObj(
            loginTries=1,
            searchPath="",
            existenceTest=None,
            username=_username,
            password=_password,
            loginTimeout=_loginTimeout,
            commandTimeout=_commandTimeout,
            keyPath=_keyPath,
            concurrentSessions=_concurrentSessions,
        )
        self._poolkey = hash((_username, _password, self.manageIp, self.port))
        self._pool = getPool(SshRunner.POOLNAME)

    @defer.inlineCallbacks
    def connect(self, task):
        """Establish a connection with the device."""
        self.task = task
        yield self._setupConnector()
        self.connection = yield self._establishConnection()
        log.debug(
            "Connection established  device=%s manage-ip=%s",
            self.deviceId,
            self.manageIp,
        )
        self.connection.tasks.add(self.task)
        # cleanUpPool called when connection is closed, see MySshClient
        self.connection.close_defer.addCallback(self.cleanUpPool)

    @defer.inlineCallbacks
    def _setupConnector(self):
        """
        Create a new connection object for the pool if it doesn't exist.
        Set up a list for storing deferred objects that will callback
        or errback based on the result of the initial deferred.
        """
        if self._poolkey in self._pool:
            log.debug(
                "Connector already in pool  device=%s pool-key=%s",
                self.deviceId,
                self._poolkey,
            )
            defer.returnValue(None)

        connection = self.client(
            self.deviceId,
            self.manageIp,
            self.port,
            options=self._sshOptions,
        )
        self._pool[self._poolkey] = []

        try:
            connection = yield connection.run()
        except Exception as e:
            self.cleanUpPool(connection)
            log.error("Failed to set up connection  error=%s", e)
            raise e
        else:
            deferredList = self._pool.get(self._poolkey, [])
            self._pool[self._poolkey] = connection
            for d in deferredList:
                d.callback(connection)

    def _establishConnection(self):
        """
        Either creates a deferred to append to the pool list otherwise, wraps
        the result
        """
        if self._poolkey not in self._pool:
            return defer.fail(RuntimeError("No connector found"))

        connection_or_list = self._pool.get(self._poolkey)
        if isinstance(connection_or_list, list):
            d = defer.Deferred()
            connection_or_list.append(d)
        else:
            d = defer.succeed(connection_or_list)
        return d

    def send(self, datasource):
        """
        Create a channel on the connection and send the command

        @type datasource: Products.ZenRRD.zencommand.Cmd
        """
        self.datasource = datasource
        self._deferred = self.connection.addCommand(datasource.command)
        self._deferred.addBoth(self.processEnded)
        log.debug(
            "Command sent  device=%s command=%r",
            self.deviceId,
            datasource.command,
        )
        return self._deferred

    def close(self):
        """
        Discard the task and close the connection if there are no remaining
        tasks
        """
        if self.connection:
            self.connection.tasks.discard(self.task)
            if not self.connection.tasks:
                # Last task is using connection so can be closed
                self.connection.clientFinished()
                self.cleanUpPool(close=True)
                log.debug("Connection closed  connection=%s", self.connection)
            self.connection = None
        else:
            log.debug("No connection to close")

    def cleanUpPool(self, connection=None, close=False):
        """
        Deletes the connection from the pool (if it exists)
        """
        connection = connection or self.connection

        if self._poolkey in self._pool:
            # Cancel the deferreds from other tasks waiting on a connection.
            content = self._pool.get(self._poolkey)
            if isinstance(content, list):
                for d in content:
                    if not d.called:
                        d.cancel()
            del self._pool[self._poolkey]
            log.debug(
                "Deleted connection from pool  device=%s connection=%s",
                self.deviceId,
                connection,
            )
        if close and connection and hasattr(connection, "transport"):
            connection.transport.loseConnection()

    def processEnded(self, result):
        """
        Deliver ourselves to the starter with the proper attributes
        """
        if isinstance(result, Failure):
            log.debug(
                "Command failed  device=%s failure=%r", self.deviceId, result
            )
            return result

        self.output, self.exitCode, self.stderr = result

        if (
            not self.connection.is_expired
            and self.stderr in SshRunner.EXPIRED_MESSAGES
        ):
            log.debug(
                "Connection expired, cleaning up pool  "
                "device=%s connection=%s",
                self.deviceId,
                self.connection.description,
            )
            self.connection.is_expired = True
            self.cleanUpPool(close=True)

        return self
