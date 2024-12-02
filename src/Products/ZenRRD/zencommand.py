##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, 2010, 2012,  all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ZenCommand

Run Command plugins periodically.

"""

import logging
import time
import traceback

from collections import defaultdict
from copy import copy
from datetime import datetime, timedelta
from functools import partial
from pprint import pformat

from twisted.internet import defer
from twisted.python.failure import Failure
from twisted.spread import pb
from zope.component import queryUtility
from zope.interface import implementer

from Products.DataCollector.SshClient import SshClient
from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import (
    ICollectorPreferences,
    IDataService,
    IEventService,
    IPausingScheduledTask,
)
from Products.ZenCollector.tasks import (
    BaseTask,
    SimpleTaskFactory,
    SubConfigurationTaskSplitter,
    TaskStates,
)
from Products.ZenEvents.ZenEventClasses import Clear, Cmd_Fail, Error, Info
from Products.ZenRRD import runner
from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenUtils.Executor import makeExecutor
from Products.ZenUtils.Utils import getExitMessage

# The following classes were refactored into the runner module after the
# 4.2 release. ZenPacks were importing those classes from here, so they
# must be exported for backwards compatibility.
ProcessRunner = runner.ProcessRunner
ProcessRunner.start = ProcessRunner.send
SshRunner = runner.SshRunner
SshRunner.start = SshRunner.send
TimeoutError = runner.TimeoutError

MAX_CONNECTIONS = 250
MAX_BACK_OFF_MINUTES = 20

COLLECTOR_NAME = "zencommand"

log = logging.getLogger("zen.zencommand")


@implementer(ICollectorPreferences)
class SshPerformanceCollectionPreferences(object):
    def __init__(self):
        """Initialize a SshPerformanceCollectionPreferences instance."""
        self.collectorName = COLLECTOR_NAME
        self.configCycleInterval = 20  # minutes
        self.cycleInterval = 5 * 60  # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = (
            "Products.ZenHub.services.CommandPerformanceConfig"
        )

        # Provide a reasonable default for the max number of tasks
        self.maxTasks = 50

        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        parser.add_option(
            "--showrawresults",
            dest="showrawresults",
            action="store_true",
            default=False,
            help="Show the raw RRD values. For debugging purposes only.",
        )

        parser.add_option(
            "--maxbackoffminutes",
            dest="maxbackoffminutes",
            default=MAX_BACK_OFF_MINUTES,
            type="int",
            help="When a device fails to respond, increase the time to"
            " check on the device until this limit.",
        )

        parser.add_option(
            "--showfullcommand",
            dest="showfullcommand",
            action="store_true",
            default=False,
            help="Display the entire command and command-line arguments, "
            " including any passwords.",
        )

        parser.add_option(
            "--datasource",
            dest="datasource",
            type="string",
            default=None,
            help="Collect just for one datasource. "
            "Write in format 'template/datasource'",
        )

    def postStartup(self):
        pass


class SshPerCycletimeTaskSplitter(SubConfigurationTaskSplitter):
    subconfigName = "datasources"

    def makeConfigKey(self, config, subconfig):
        return (
            config.id,
            subconfig.cycleTime,
            "Remote" if subconfig.useSsh else "Local",
        )


@implementer(runner.IClient)
class MySshClient(SshClient):
    """
    Connection to SSH server at the remote device
    """

    def __init__(self, *args, **kw):
        super(MySshClient, self).__init__(*args, **kw)

        self.connect_defer = None
        self.close_defer = None
        self.command_defers = {}

        # If True, the connection is closed at the end of the collection cycle.
        self.timed_out = False

        self.description = "%s:*****@%s:%s" % (
            self.username,
            self.ip,
            self.port,
        )
        self.tasks = set()
        self.is_expired = False  # TODO: placeholder; not implemented yet

    def __str__(self):
        return self.description

    def run(self):
        d = self.connect_defer = defer.Deferred()
        self.close_defer = defer.Deferred()
        super(MySshClient, self).run()
        return d

    def serviceStarted(self, sshconn):
        super(MySshClient, self).serviceStarted(sshconn)
        self.connect_defer.callback(self)

    def addCommand(self, command):
        """
        Run a command against the server
        """
        d = self.command_defers[command] = defer.Deferred()
        super(MySshClient, self).addCommand(command)
        return d

    def addResult(self, command, data, code, stderr):
        """
        Forward the results of the command execution to the starter
        """
        # don't call the CollectorClient.addResult which adds the result to a
        # member variable for zenmodeler
        d = self.command_defers.pop(command, None)
        if d is None:
            log.error(
                "Internal error where deferred object not in dictionary  "
                "description=%s command=%r data=%r code=%s stderr=%r",
                self.description,
                command.split()[0],
                data,
                code,
                stderr,
            )
        elif not d.called:
            d.callback((data, code, stderr))

    def clientConnectionLost(self, connector, reason):
        # Connection was lost, but could be because we just closed it. Not
        # necessarily cause for concern.
        msg = "Connection lost  description=%s" % self.description
        log.debug(msg)
        if self.connect_defer and not self.connect_defer.called:
            self.connect_defer.errback(reason)
        if self.close_defer and not self.close_defer.called:
            self.close_defer.callback(msg)

    def check(self, ip, timeout=2):
        """
        Turn off blocking SshClient.test method
        """
        return True

    def clientFinished(self, error=None):
        """
        We don't need to track commands/results when they complete
        """
        super(MySshClient, self).clientFinished()
        self.cmdmap = {}
        self._commands = []
        self.results = []
        if error:
            self.connect_defer.errback(error)

    def clientConnectionFailed(self, connector, reason):
        """
        If we didn't connect let the modeler know

        @param connector: connector associated with this failure
        @type connector: object
        @param reason: failure object
        @type reason: object
        """
        if self.connect_defer and not self.connect_defer.called:
            self.connect_defer.errback(reason)
        if self.close_defer and not self.close_defer.called:
            self.close_defer.errback(reason)
        self.clientFinished()


class DataPointConfig(pb.Copyable, pb.RemoteCopy):
    id = ""
    component = ""
    rrdPath = ""
    rrdType = None
    rrdCreateCommand = ""
    rrdMin = None
    rrdMax = None
    metadata = None

    def __init__(self):
        self.data = {}

    def __repr__(self):
        return pformat((self.data, self.id))


pb.setUnjellyableForClass(DataPointConfig, DataPointConfig)


class Cmd(pb.Copyable, pb.RemoteCopy):
    """
    The configuration for collecting the performance data from one datasource.
    """

    # Attributes populated by the CommandPerformanceConfig service
    useSsh = False
    name = ""
    cycleTime = None
    component = None
    eventClass = None
    eventKey = None
    severity = 3
    parser = None
    ds = None
    points = None  # DataPointConfigs ...?
    env = None
    command = None

    # Attributes populated if Cmd is for an OSProcess component.
    includeRegex = None
    excludeRegex = None
    replaceRegex = None
    replacement = None
    primaryUrlPath = None
    generatedId = None
    displayName = None
    sequence = None

    # Attributes populated when the command is run.
    lastStart = 0
    lastStop = 0

    def __init__(self):
        self.points = []

    def processCompleted(self, result):
        self.lastStop = time.time()

        # Ensure that the lastStop and lastStart values are sane.
        if self.lastStop < self.lastStart:
            log.debug("System clock went back?")
            self.lastStop = self.lastStart

        if not isinstance(result, Failure):
            if result.output is None:
                result.output = ""
            if result.stderr is None:
                result.stderr = ""

        return result

    def getEventKey(self, point):
        # get datapoint name and add it to the event key
        dpName = point.rrdPath.split("/")[-1]
        if dpName == "":
            try:
                dpName = point.dpName
            except AttributeError:
                dpName = ""

        return self.eventKey + "|" + dpName

    def commandKey(self):
        """Provide a value that establishes the uniqueness of this command"""
        return "%".join(
            map(
                str, [self.useSsh, self.cycleTime, self.severity, self.command]
            )
        )

    def __str__(self):
        return " ".join(
            map(str, [self.ds, "useSSH=%s" % self.useSsh, self.cycleTime])
        )


pb.setUnjellyableForClass(Cmd, Cmd)


STATUS_EVENT = {
    "eventClass": Cmd_Fail,
    "component": "command",
}


@implementer(IPausingScheduledTask)
class SshPerformanceCollectionTask(BaseTask):
    """
    A task that performs periodic performance collection for devices providing
    data via SSH connections.
    """

    STATE_CONNECTING = "CONNECTING"
    STATE_FETCH_DATA = "FETCH_DATA"
    STATE_PARSE_DATA = "PARSING_DATA"
    STATE_STORE_PERF = "STORE_PERF_DATA"

    def __init__(
        self, taskName, configId, scheduleIntervalSeconds, taskConfig
    ):
        """
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param configId: configuration to watch
        @type configId: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(SshPerformanceCollectionTask, self).__init__(
            taskName, configId, scheduleIntervalSeconds, taskConfig
        )

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = taskConfig.id
        self._manageIp = taskConfig.manageIp

        # NOTE: taskConfig.datasources is a list of Cmd objects.
        self._datasources = taskConfig.datasources

        self._useSsh = any(ds.useSsh for ds in self._datasources)
        client = MySshClient if self._useSsh else None
        self._runner = partial(runner.getRunner, taskConfig, client)
        self._connector = self._runner()

        self._dataService = queryUtility(IDataService)
        self._eventService = queryUtility(IEventService)

        preferences = queryUtility(ICollectorPreferences, COLLECTOR_NAME)
        self._maxbackoffseconds = preferences.options.maxbackoffminutes * 60
        self._showfullcommand = preferences.options.showfullcommand
        self._chosenDatasource = preferences.options.datasource

        # Associate commands to datasources.
        # Set _commandMap *after* _chosenDatasource has been set.
        self._commandMap = _groupCommands(self.getDatasources(), self._device)

        self._executor = makeExecutor(limit=taskConfig.zSshConcurrentSessions)

        self.executed = 0
        self._lastErrorMsg = ""

        self.manage_ip_event = {
            "eventClass": Cmd_Fail,
            "device": self._devId,
            "summary": (
                "IP address not set, collection will be attempted "
                "with host name"
            ),
            "component": COLLECTOR_NAME,
            "eventKey": "Empty_IP_address",
        }

    def __str__(self):
        return "COMMAND schedule Name: %s configId: %s Datasources: %d" % (
            self.name,
            self.configId,
            len(self._datasources),
        )

    def cleanup(self):
        if self._connector:
            self._connector.close()

    @defer.inlineCallbacks
    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: Deferred actions to run against a device configuration
        @rtype: Twisted deferred object
        """
        if self._scheduler.cyberark:
            old_pass = self._device.zCommandPassword
            old_name = self._device.zCommandUsername
            yield self._scheduler.cyberark.update_config(
                self._devId, self._device
            )
            if (
                old_pass != self._device.zCommandPassword
                or old_name != self._device.zCommandUsername
            ):
                self._connector.close()
                self.__init__(
                    self.name, self.configId, self.interval, self._device
                )

        log.debug(
            "Starting collection task  device=%s interval=%s",
            self._devId,
            self.interval,
        )
        self._doTask_start = datetime.now()
        self.state = SshPerformanceCollectionTask.STATE_CONNECTING

        try:
            if not self._manageIp and self._useSsh:
                self._eventService.sendEvent(
                    self.manage_ip_event, severity=Info
                )
            else:
                self._eventService.sendEvent(
                    self.manage_ip_event, severity=Clear
                )

            yield self._connector.connect(self)

            if self._useSsh:
                msg = "Connected to %s [%s]" % (self._devId, self._manageIp)
                self._eventService.sendEvent(
                    STATUS_EVENT,
                    device=self._devId,
                    summary=msg,
                    component=COLLECTOR_NAME,
                    severity=Clear,
                )

            raw = yield self._fetchPerf()
            parsed = self._parseResults(raw)
            yield self._storeResults(parsed)

            # If a channel timed out, close the connection.
            if self._connector.connection:
                if self._connector.connection.timed_out:
                    self._connector.close()
                    log.info(
                        "Connection closed  device=%s reason=%s",
                        self._devId,
                        "timeout",
                    )
        except defer.CancelledError:
            message = "Twisted deferred was cancelled."
            log.debug(
                "Connection lost  device=%s ip=%s interval=%s description=%s",
                self._devId,
                self._manageIp,
                self.interval,
                message,
            )

        except Exception as e:
            self.state = TaskStates.STATE_PAUSED
            err_msg = "Task paused  device=%s ip=%s interval=%s message=%s" % (
                self._devId,
                self._manageIp,
                self.interval,
                e,
            )
            if log.isEnabledFor(logging.DEBUG):
                log.exception(err_msg)
            else:
                log.error(err_msg)
            self._eventService.sendEvent(
                STATUS_EVENT,
                device=self._devId,
                summary=str(e),
                component=COLLECTOR_NAME,
                severity=Error,
            )
            # Re-raise the exception to the scheduler, which will increment
            # the failed task counter.
            raise
        else:
            self._returnToNormalSchedule()

    def getDatasources(self):
        if self._chosenDatasource:
            return [
                ds
                for ds in self._datasources
                if ds.name == self._chosenDatasource
            ]

        return self._datasources

    def _fetchFromDatasource(self, datasource):
        """Creates a new IRunner instance to run the datasource command.

        A Deferred is returned which returns the datasource populated with
        the command's results, or the Failure if the command failed or
        timed out.

        @type datasource: Products.ZenRRD.zencommand.Cmd
        @rtype: twisted.internet.defer.Deferred
        """
        d = self._runner(self._connector.connection).send(datasource)
        if self._showfullcommand:
            log.info(
                "Datasource added  device=%s interval=%s name=%s command=%r",
                self._devId,
                self.interval,
                datasource.name,
                datasource.command,
            )
        datasource.lastStart = time.time()
        d.addBoth(datasource.processCompleted)
        return d

    @defer.inlineCallbacks
    def _fetchPerf(self):
        """Retrieve the performance data from the device.

        Sends commands to run the monitored device then waits for and
        processes the results.
        """
        log.debug(
            "Fetching data  device=%s interval=%s", self._devId, self.interval
        )
        self.state = SshPerformanceCollectionTask.STATE_FETCH_DATA

        try:
            # Collect the Deferred objects into this list.
            pending = []

            label = "{}/{}".format(self.interval, self._devId)
            # Submit the commands to the executor.
            for command, datasources in self._commandMap.items():
                first_ds = datasources[0]
                call = partial(self._fetchFromDatasource, first_ds)
                # Note: 'd' is not the same deferred object returned from
                # the _fetchFromDatasource method.
                d = self._executor.submit(
                    call,
                    timeout=self._device.zCommandCommandTimeout,
                    label=label,
                )
                d.addCallback(self._handle_completion, command)
                d.addErrback(self._handle_error, command)
                pending.append(d)

            # Wait for all the results to return.
            results = yield defer.DeferredList(pending)

            # Restructure the results data from
            # (success, (success, (command, runner/failure)))
            # to
            # (success, (command, runner/failure))
            results = tuple(data for _, data in results)

            defer.returnValue(results)
        except Exception:
            log.exception("Problem while fetching data")
            raise

    def _handle_completion(self, response, command):
        # This callback method is called when the command finishes normally.
        # "Normally" also means non-zero exit codes.
        return (True, (command, response))

    def _handle_error(self, failure, command):
        log.debug(
            "Datasource command failed  "
            "device=%s interval=%s command=%r failure=%r",
            self._devId,
            self.interval,
            command,
            failure,
        )
        # This callback method is called for any error resulting from the
        # command being unable to complete, e.g. timeouts.
        return (False, (command, failure))

    def _process_os_processes_results_in_sequence(self, datasources, response):
        """
        Process OSProcesses in sequence order to avoid more than one OSProcess
        match the same process

        @param datasources: list of OSProcess datasources
        @type datasources: List[Cmd]
        @param response: the results of the command
        @type response: IRunner (typically SshRunner)
        """
        process_parseable_results = []

        # Sort the datasources by sequence
        datasources.sort(key=lambda x: x.sequence)

        already_matched = []

        # Now we process datasources in sequence order
        for ds in datasources:
            parsed = ParsedResults()
            ds.result = copy(response)
            ds.already_matched_cmdAndArgs = already_matched
            self._processDatasourceResults(ds, response, parsed)
            already_matched = ds.already_matched_cmdAndArgs[:]
            del ds.already_matched_cmdAndArgs
            process_parseable_results.append((ds, parsed))

        return process_parseable_results

    def _parseResults(self, resultList):
        """
        Interpret the results retrieved from the commands and pass on
        the datapoint values and events.

        @parameter resultList: results of running the commands
        @type resultList: array of (boolean, (str, IRunner|Failure))
        """
        log.debug(
            "Parsing fetched data  device=%s interval=%s",
            self._devId,
            self.interval,
        )
        self.state = SshPerformanceCollectionTask.STATE_PARSE_DATA

        parsed_results = []
        for success, (command, result) in resultList:
            parse = self._parse_result if success else self._parse_error
            datasources = self._commandMap.get(command)
            if datasources:
                parsed_results.extend(parse(datasources, result))
        return parsed_results

    def _timeout_error_result(self, datasource):
        parsed = ParsedResults()
        parsed.events.append(makeCmdTimeoutEvent(self._devId, datasource))
        return parsed

    def _handle_timeout_error(self, datasources, failure):
        if self._connector.connection:
            self._connector.connection.timed_out = True
        log.warn(
            "Command timed out.  Connection flagged for closure  "
            "device=%s interval=%s datasources=%s",
            self._devId,
            self.interval,
            ",".join(ds.name for ds in datasources),
        )
        return self._timeout_error_result

    def _failure_error_result(self, failure, datasource):
        parsed = ParsedResults()
        event = makeCmdEvent(self._devId, datasource, "Could not run command")
        event["error"] = str(failure.type)
        event["reason"] = str(failure.value)
        parsed.events.append(event)
        # Clear the timeout event since this command didn't time out.
        parsed.events.append(
            makeCmdTimeoutEvent(self._devId, datasource, severity=Clear),
        )
        return parsed

    def _handle_failure_error(self, datasources, failure):
        log.error(
            "Command failed  "
            "device=%s interval=%s datasource=%s error=%s reason=%s",
            self._devId,
            self.interval,
            datasources[0].name,
            failure.type,
            failure.value,
        )
        return partial(self._failure_error_result, failure)

    def _unexpected_error_result(self, response, datasource):
        event = makeCmdEvent(
            self._devId, datasource, "Unexpected result from command"
        )
        event["result"] = str(response)
        if self._showfullcommand:
            event["command"] = datasource.command
        parsed = ParsedResults()
        parsed.events.append(event)
        # Clear the timeout event since this command didn't time out.
        parsed.events.append(
            makeCmdTimeoutEvent(self._devId, datasource, severity=Clear),
        )
        return parsed

    def _handle_unexpected_error(self, datasources, response):
        log.error(
            "Command failed with unexpected result  "
            "device=%s interval=%s datasources=%s result=%s",
            self._devId,
            self.interval,
            ",".join(ds.name for ds in datasources),
            response,
        )
        return partial(self._unexpected_error_result, response)

    def _parse_error(self, datasources, failure):
        if isinstance(failure, Failure):
            if failure.check(defer.TimeoutError):
                get_results = self._handle_timeout_error(datasources, failure)
            else:
                get_results = self._handle_failure_error(datasources, failure)
        else:
            get_results = self._handle_unexpected_error(datasources, failure)

        return [(ds, get_results(ds)) for ds in datasources]

    def _parse_result(self, datasources, response):
        ds = datasources[0]
        log.debug(
            "Command succeeded  "
            "device=%s interval=%s datasource=%s elapsed-seconds=%.2f",
            self._devId,
            self.interval,
            ",".join(ds.name for ds in datasources),
            ds.lastStop - ds.lastStart,
        )

        # Process all OSProcess/ps datasources to avoid more than one
        # OSProcess matching the same process
        if ds.name == "OSProcess/ps":
            return self._process_os_processes_results_in_sequence(
                datasources,
                response,
            )

        results = []
        for ds in datasources:
            parsedResults = ParsedResults()
            self._processDatasourceResults(ds, response, parsedResults)
            results.append((ds, parsedResults))

        return results

    def _processDatasourceResults(self, datasource, response, parsed):
        """
        Process a single datasource's results

        @parameter datasource: Data about datasource
        @type datasource: Cmd object
        @parameter response: Result of the datasource command
        @type response: an IRunner object (SshRunner)
        @parameter parsed: Parsed results are added to this object.
        @type parsed: ParsedResults object
        """
        exitCode = response.exitCode
        datasource.result = copy(response)
        output = response.output.strip()
        stderr = response.stderr.strip()

        if exitCode == 0 and not output:
            msg = "No data returned for command"
            if self._showfullcommand:
                msg += ": %s" % datasource.command
            log.warn("%s %s %s", self.name, datasource.name, msg)

            event = makeCmdEvent(self._devId, datasource, msg)
            if self._showfullcommand:
                event["command"] = datasource.command
            if stderr:
                event["stderr"] = stderr
            parsed.events.append(event)
            return

        try:
            operation = "Creating Parser"
            parser = datasource.parser.create()

            operation = "Running Parser"
            parser.preprocessResults(datasource, log)
            parser.processResults(datasource, parsed)

            if not parsed.events and parser.createDefaultEventUsingExitCode:
                if exitCode == 0:
                    msg = ""
                    severity = Clear
                else:
                    msg = "Datasource: %s - Code: %s - Msg: %s" % (
                        datasource.name,
                        exitCode,
                        getExitMessage(exitCode),
                    )
                    severity = datasource.severity
                event = makeCmdEvent(
                    self._devId,
                    datasource,
                    msg,
                    severity=severity,
                )
                parsed.events.append(event)

            # Clear any timeout event
            parsed.events.append(
                makeCmdTimeoutEvent(self._devId, datasource, severity=Clear),
            )

            if stderr:
                # Add the stderr output to the error events.
                # Note: although the command succeeded, the parser may put an
                # error event into the results.
                for event in parsed.events:
                    if event["severity"] not in ("Clear", "Info", "Debug"):
                        event["stderr"] = stderr
        except Exception:
            msg = "Error %s %s" % (operation, datasource.parser)
            log.exception(msg)
            event = makeCmdEvent(self._devId, datasource, msg)
            event["message"] = traceback.format_exc()
            event["output"] = output
            if stderr:
                event["stderr"] = stderr
            parsed.events.append(event)
        else:
            # Determine whether a non-timeout related event exists.
            hasNonTimeoutEvent = any(
                (
                    event.get("eventKey") == datasource.eventKey
                    for event in parsed.events
                )
            )
            if not hasNonTimeoutEvent:
                # No existing non-timeout event, so add a Clear event to
                # clear any prior events on this datasource.
                parsed.events.append(
                    makeCmdEvent(
                        self._devId,
                        datasource,
                        "Datasource %s command completed successfully"
                        % datasource.name,
                        severity=Clear,
                    ),
                )

    @defer.inlineCallbacks
    def _storeResults(self, resultList):
        """
        Store the values in RRD files

        @parameter resultList: results of running the commands
        @type resultList: array of tuples which have the following layout:
           (Cmd object, ParsedResults object)
        """
        log.debug(
            "Store parsed data  device=%s interval=%s",
            self._devId,
            self.interval,
        )
        self.state = SshPerformanceCollectionTask.STATE_STORE_PERF

        try:
            # Note:
            #   'datasource' is a Cmd object.
            #   'results' is a ParsedResults object.
            for datasource, results in resultList:
                log.debug(
                    "Store values  device=%s interval=%s datasource=%s",
                    self._devId,
                    self.interval,
                    datasource.name,
                )
                for dp, value in results.values:
                    log.debug(
                        "Store datapoint  "
                        "device=%s interval=%s datasource=%s datapoint=%s",
                        self._devId,
                        self.interval,
                        datasource.name,
                        dp.dpName,
                    )
                    threshData = {
                        "eventKey": datasource.getEventKey(dp),
                        "component": dp.component,
                    }
                    try:
                        if self._chosenDatasource:
                            log.info(
                                "Component: %s >> DataPoint: %s %s",
                                dp.metadata["contextKey"],
                                dp.dpName,
                                value,
                            )
                        yield self._dataService.writeMetricWithMetadata(
                            dp.dpName,
                            value,
                            dp.rrdType,
                            min=dp.rrdMin,
                            max=dp.rrdMax,
                            threshEventData=threshData,
                            metadata=dp.metadata,
                        )
                    except Exception as e:
                        log.exception(
                            "Failed to write to metric service  "
                            "device=%s interval=%s datasource=%s datapoint=%s "
                            "metadata=%s type=%s message=%s",
                            self._devId,
                            self.interval,
                            datasource.name,
                            dp.dpName,
                            dp.metadata,
                            e.__class__.__name__,
                            e,
                        )

                # Send accumulated events
                for event in results.events:
                    self._eventService.sendEvent(event, device=self._devId)

            doTask_end = datetime.now()
            duration = doTask_end - self._doTask_start
            max_duration = timedelta(seconds=self.interval)
            if duration <= max_duration:
                logf = log.debug
                adjective = "Nominal"
            else:
                logf = log.warn
                adjective = "Excessive"
            logf(
                "%s collection run time  "
                "config-id=%s duration=%.1f cycle-interval=%s",
                adjective,
                self.configId,
                duration.total_seconds(),
                self.interval,
            )
        except Exception:
            log.exception("Problem while storing data")

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = "%s useSSH: %s\n" % (self.name, self._useSsh)
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display

    def pause(self):
        self.cleanup()

    def resume(self):
        pass


def _groupCommands(datasources, config):
    # Map commands to datasources.  The same command may be used by
    # different datasources.  There's no reason to run the same command
    # multiple times.
    commands = defaultdict(list)
    for datasource in datasources:
        # 'deviceConfig' is required by some command output parsers.
        datasource.deviceConfig = config
        commands[datasource.command].append(datasource)
    return commands


def makeCmdTimeoutEvent(deviceId, datasource, severity=None):
    """Return a new command timed out event.

    @param deviceId: The ID of the device where the command timed out.
    @type deviceId: str

    @param datasource: The datasource associated with the command.
    @type datasource: Products.ZenRRD.zencommand.Cmd

    @param severity: The event's severity level
    @type severity: int
    """
    return makeCmdEvent(
        deviceId,
        datasource,
        "Datasource %s command timed out" % datasource.name,
        severity=Error if severity is None else severity,
        eventKey="{}_timeout".format(datasource.eventKey),
    )


def makeCmdEvent(deviceId, datasource, msg, severity=None, eventKey=None):
    """
    Create an event using the info in the Cmd object.
    """
    return {
        "device": deviceId,
        "component": datasource.component,
        "eventClass": datasource.eventClass,
        "eventKey": datasource.eventKey if eventKey is None else eventKey,
        "severity": datasource.severity if severity is None else severity,
        "summary": msg,
    }


if __name__ == "__main__":
    # Required for passing classes from zenhub to here
    from Products.ZenRRD.zencommand import Cmd, DataPointConfig

    myPreferences = SshPerformanceCollectionPreferences()
    myTaskFactory = SimpleTaskFactory(SshPerformanceCollectionTask)
    myTaskSplitter = SshPerCycletimeTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
