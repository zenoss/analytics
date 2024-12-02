##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import sys

from twisted.internet import protocol

from .BaseClient import BaseClient

log = logging.getLogger("zen.CmdClient")


class CollectorClient(BaseClient, protocol.ClientFactory):
    """
    Data collector client class to be subclassed by different types
    collector protocols.

    Some z-properties to regulate a CollectorClient's behavior:

        zCommandLoginTries - number of times to attempt to login
        zCommandPathList - list of paths to check for a command
        zCommandExistanceCheck - shell command issued to look for an
            executable must echo succ if the executable is found.
            default: test -f executable
    """

    maintainConnection = False
    cmdindex = 0

    def __init__(
        self,
        hostname,
        ip,
        port,
        plugins=None,
        options=None,
        device=None,
        datacollector=None,
        alog=None,
    ):
        """
        Gather our required zProperties

        @param hostname: name of the remote device
        @type hostname: string
        @param ip: IP address of the remote device
        @type ip: string
        @param port: IP port number to listen on
        @type port: integer
        @param plugins: plugins to run
        @type plugins: list
        @param options: optparse options
        @type options: optparse options object
        @param device: DMD device object
        @type device: device object
        @param datacollector: datacollector
        @type datacollector: datacollector object
        @param alog: Python logging class object  (unused)
        @type alog: Python logging class object
        """
        BaseClient.__init__(self, device, datacollector)

        self.hostname = hostname
        self.ip = ip
        self.port = port
        plugins = plugins or []
        self.cmdmap = {}
        self._commands = []
        for plugin in plugins:
            self.cmdmap[plugin.command] = plugin
            self._commands.append(plugin.command)
        self.results = []
        self.protocol = None

        if options:
            defaultUsername = options.username
            defaultPassword = options.password
            defaultLoginTries = options.loginTries
            defaultLoginTimeout = options.loginTimeout
            defaultCommandTimeout = options.commandTimeout
            defaultKeyPath = options.keyPath
            defaultConcurrentSessions = options.concurrentSessions
            defaultSearchPath = options.searchPath
            defaultExistanceTest = options.existenceTest

        if device:
            self.username = getattr(
                device, "zCommandUsername", defaultUsername
            )
            self.password = getattr(
                device, "zCommandPassword", defaultPassword
            )
            self.loginTries = getattr(
                device, "zCommandLoginTries", defaultLoginTries
            )
            self.loginTimeout = getattr(
                device, "zCommandLoginTimeout", defaultLoginTimeout
            )
            self.commandTimeout = getattr(
                device, "zCommandCommandTimeout", defaultCommandTimeout
            )
            self.keyPath = getattr(device, "zKeyPath", defaultKeyPath)
            self.concurrentSessions = getattr(
                device, "zSshConcurrentSessions", defaultConcurrentSessions
            )
            self.port = getattr(device, "zCommandPort", self.port)
            self.searchPath = getattr(
                device, "zCommandSearchPath", defaultSearchPath
            )
            self.existenceTest = getattr(
                device, "zCommandExistanceTest", defaultExistanceTest
            )
        else:
            self.username = defaultUsername
            self.password = defaultPassword
            self.loginTries = defaultLoginTries
            self.loginTimeout = defaultLoginTimeout
            self.commandTimeout = defaultCommandTimeout
            self.keyPath = defaultKeyPath
            self.concurrentSessions = defaultConcurrentSessions
            self.searchPath = defaultSearchPath
            self.existenceTest = defaultExistanceTest

    def addCommand(self, command):
        """
        Add a command to the list of commands to gather data

        @param command: command
        @type command: string
        """
        if isinstance(command, basestring):
            self._commands.append(command)
        else:
            self._commands.extend(command)

    def addResult(self, command, data, exitCode, stderr=None):
        """
        Add a result pair to the results store

        @param command: command
        @type command: string
        @param data: results of running the command
        @type data: string
        @param exitCode: exit code from executing the command
        @type exitCode: integer
        """
        plugin = self.cmdmap.get(command, None)
        self.results.append((plugin, data))

    def getCommands(self):
        """
        The commands which we will use to collect data

        @return: commands
        @rtype: list of strings
        """
        return self._commands

    def getResults(self):
        """
        Return all of the results we have collected so far

        @return: results
        @rtype: list of strings
        """
        return self.results

    def commandsFinished(self):
        """
        Called by protocol to see if all commands have been run
        """
        return len(self.results) == len(self._commands)

    def clientFinished(self, error=None):
        """
        Tell the datacollector that we are all done
        """
        log.info("command client finished collection for %s", self.hostname)
        self.cmdindex = 0
        if self.datacollector:
            self.datacollector.clientFinished(self)

    def reinitialize(self):
        """
        Clear out all member variables that are collections to avoid memory
        leaks.
        """
        self.cmdmap = {}
        self._commands = []
        self.results = []


def buildOptions(parser=None, usage=None):
    """
    Build a list of command-line options we will accept

    @param parser: optparse parser
    @type parser: optparse object
    @param usage: description of how to use the program
    @type usage: string
    @return: optparse parser
    @rtype: optparse object
    """

    # Default option values
    defaultUsername = os.environ.get("USER", "")
    defaultPassword = ""
    defaultLoginTries = 1
    defaultLoginTimeout = 10
    defaultCommandTimeout = 10
    defaultKeyPath = "~/.ssh/id_dsa"
    defaultConcurrentSessions = 10
    defaultSearchPath = []
    defaultExistanceTest = "test -f %s"

    if not usage:
        usage = "%prog [options] hostname[:port] command"

    if not parser:
        from optparse import OptionParser

        parser = OptionParser(
            usage=usage,
        )

    parser.add_option(
        "-u",
        "--user",
        dest="username",
        default=defaultUsername,
        help="Login username",
    )
    parser.add_option(
        "-P",
        "--password",
        dest="password",
        default=defaultPassword,
        help="Login password",
    )
    parser.add_option(
        "-t",
        "--loginTries",
        dest="loginTries",
        default=defaultLoginTries,
        type="int",
        help="Number of times to attempt to login",
    )
    parser.add_option(
        "-L",
        "--loginTimeout",
        dest="loginTimeout",
        type="float",
        default=defaultLoginTimeout,
        help="Timeout period (secs) to find login expect statments",
    )
    parser.add_option(
        "-T",
        "--commandTimeout",
        dest="commandTimeout",
        type="float",
        default=defaultCommandTimeout,
        help="Timeout period (secs) after issuing a command",
    )
    parser.add_option(
        "-K",
        "--keyPath",
        dest="keyPath",
        default=defaultKeyPath,
        help="Path to use when looking for SSH keys",
    )
    parser.add_option(
        "-S",
        "--concurrentSessions",
        dest="concurrentSessions",
        type="int",
        default=defaultConcurrentSessions,
        help="Allowable number of concurrent SSH sessions",
    )
    parser.add_option(
        "-s",
        "--searchPath",
        dest="searchPath",
        default=defaultSearchPath,
        help="Path to use when looking for commands",
    )
    parser.add_option(
        "-e",
        "--existenceTest",
        dest="existenceTest",
        default=defaultExistanceTest,
        help="How to check if a command is available or not",
    )
    if not parser.has_option("-v"):
        parser.add_option(
            "-v",
            "--logseverity",
            dest="logseverity",
            default=logging.INFO,
            type="int",
            help="Logging severity threshold",
        )
    return parser


def parseOptions(parser, port):
    """
    Command-line option parser

    @param parser: optparse parser
    @type parser: optparse object
    @param port: IP port number to listen on
    @type port: integer
    @return: parsed options
    @rtype: object
    """
    options, args = parser.parse_args()
    if len(args) < 2:
        parser.print_help()
        sys.exit(1)
    if args[0].find(":") > -1:
        hostname, port = args[0].rsplit(":", 1)
    else:
        hostname = args[0]
    options.hostname = hostname
    options.port = port
    options.commands = args[1:]
    return options
