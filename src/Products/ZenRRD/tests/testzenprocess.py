##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import os.path
import pprint

from md5 import md5
from unittest import TestCase

from Products.ZenHub.services.ProcessConfig import ProcessProxy
from Products.ZenRRD.zenprocess import mapResultsToDicts, ZenProcessTask

log = logging.getLogger("zen.testzenprocess")


class Options(object):
    pass


class Preferences(object):
    options = Options()


class EventService(object):
    def sendEvent(self, *args, **kwargs):
        pass


class TaskConfig(object):
    name = "devicename"
    manageIp = "192.168.10.10"
    zMaxOIDPerRequest = 1
    lastmodeltime = "datestring"
    snmpConnInfo = {}
    _preferences = object()
    _eventService = object()
    thresholds = []
    processes = {}

    def __init__(self, procDefs=None):
        if procDefs is not None:
            self.processes = procDefs


class ProcessResults(object):
    PROCESSES = "PROCESSES"
    AFTERBYCONFIG = "AFTERBYCONFIG"
    AFTERPIDTOPS = "AFTERPIDTOPS"
    BEFOREBYCONFIG = "BEFOREBYCONFIG"
    NEW = "NEW"
    RESTARTED = "RESTARTED"
    DEAD = "DEAD"
    MISSING = "MISSING"

    orderedKeys = (
        PROCESSES,
        AFTERBYCONFIG,
        AFTERPIDTOPS,
        BEFOREBYCONFIG,
        NEW,
        RESTARTED,
        DEAD,
        MISSING,
    )
    resultKeys = (
        AFTERBYCONFIG,
        AFTERPIDTOPS,
        BEFOREBYCONFIG,
        NEW,
        RESTARTED,
        DEAD,
        MISSING,
    )


class TestZenprocess(TestCase):
    def getFileData(self, filename):
        base = os.path.join(os.path.dirname(__file__), "zenprocess_data")
        data = None
        name = base + "/" + filename
        try:
            dataAsString = open(name).read()
            data = eval(dataAsString)
        except Exception as ex:
            log.warn(
                "Unable to evaluate data file %s because %s", name, str(ex)
            )

        self.assert_(data is not None, "No data from file %s" % filename)

        return data

    def makeTask(self, procDefs):
        # Blow away any cached config data
        if "devicename" in ZenProcessTask.DEVICE_STATS:
            del ZenProcessTask.DEVICE_STATS["devicename"]

        config = TaskConfig(procDefs=procDefs)
        task = ZenProcessTask("bogodevice", "taskname", 0, config)

        task._preferences = Preferences()
        task._preferences.options.showrawtables = False
        task._preferences.options.showprocs = False
        task._preferences.options.captureFilePrefix = ""
        task._eventService = EventService()
        return task

    def expected(
        self,
        PROCESSES=None,
        AFTERBYCONFIG=None,
        AFTERPIDTOPS=None,
        BEFOREBYCONFIG=None,
        NEW=None,
        RESTARTED=None,
        DEAD=None,
        MISSING=None,
    ):
        testValues = {}

        for key in ProcessResults.orderedKeys:
            arg = locals()[key]
            if arg is not None:
                testValues[key] = arg

        return testValues

    def compareTestFile(self, filename, task, expectedStats):
        """
        Assert that the results of running zenprocess on a specified test data
        file match the expectation.

        filename --- the name of a file in
            Products/ZenRRD/tests/zenprocess_data that conforms to the format
            expected by compareTestData
        task --- the Products.ZenRRD.zenprocess.ZenProcessTask to use when
            processing the data
        expectedStats --- tuple containing numbers for the following: procs,
            afterByConfig, afterPidToProcessStats, beforeByConfig, newPids,
            restarted

        The results are passed back from the method
        """
        data = self.getFileData(filename)
        return self.compareTestData(data, task, expectedStats)

    def compareTestData(self, data, task, expected):
        """
        Assert that the results of running zenprocess on the specified test
        data matches the expectation.

        testName --- the name of the running test, used for error logging
        data --- a dictionary that conforms to the following format:
            dict(snmpCategory->dict(snmpOID->data)):
            {
                '.1.3.6.1.2.1.25.4.2.1.2': {
                    '.1.3.6.1.2.1.25.4.2.1.2.<PID>': <process name>
                },
                '.1.3.6.1.2.1.25.4.2.1.4': {
                    '.1.3.6.1.2.1.25.4.2.1.4.<PID>': <process full path>
                },
                '.1.3.6.1.2.1.25.4.2.1.5': {
                    '.1.3.6.1.2.1.25.4.2.1.5.<PID>': <arguments>
                }
            }
            e.g.:
            {
                '.1.3.6.1.2.1.25.4.2.1.2': {
                    '.1.3.6.1.2.1.25.4.2.1.2.3127': 'mingetty'
                },
                '.1.3.6.1.2.1.25.4.2.1.4': {
                    '.1.3.6.1.2.1.25.4.2.1.4.3127': '/sbin/mingetty'
                },
                '.1.3.6.1.2.1.25.4.2.1.5': {
                    '.1.3.6.1.2.1.25.4.2.1.5.3127': 'tty1'
                }
            }
        task --- the Products.ZenRRD.zenprocess.ZenProcessTask to use when
            processing the data
        expected --- dictionary containing numbers for any/all of the keys
            defined in ProcessResults

        The results are passed back from the method
        """
        procs = task._parseProcessNames(data)
        results = task._determineProcessStatus(procs)

        actual = dict(zip(ProcessResults.resultKeys, results))
        actual[ProcessResults.PROCESSES] = procs

        # Save the results of the run
        task._deviceStats._pidToProcess = actual[ProcessResults.AFTERPIDTOPS]

        for key in expected:
            if expected[key] is not None:
                self.assert_(
                    key in actual,
                    "No results found for key %s, expected %s"
                    % (key, expected[key]),
                )
                if isinstance(expected[key], int):
                    self.assert_(
                        len(actual[key]) == expected[key],
                        "Expected %d %s, got %d (%s)"
                        % (expected[key], key, len(actual[key]), actual[key]),
                    )
                elif key in [ProcessResults.NEW, ProcessResults.DEAD]:
                    self.assert_(
                        0 == len(actual[key] - expected[key])
                        and 0 == len(expected[key] - actual[key]),
                        "Expected %s %s,\n\nGOT %s"
                        % (
                            key,
                            pprint.pformat(expected[key]),
                            pprint.pformat(actual[key]),
                        ),
                    )
                elif key in [ProcessResults.MISSING]:
                    actualSet = {each.name for each in actual[key]}
                    expectedSet = set(expected[key])
                    self.assert_(
                        0 == len(actualSet - expectedSet)
                        and 0 == len(expectedSet - actualSet),
                        "Expected %s %s,\n\nGOT %s"
                        % (
                            key,
                            pprint.pformat(expected[key]),
                            pprint.pformat(actual[key]),
                        ),
                    )
                elif key in [ProcessResults.AFTERPIDTOPS]:
                    actualKeys = actual[key].keys()
                    actualKeySet = set(actualKeys)
                    expectedKeySet = set(expected[key].keys())
                    actualValues = [
                        actual[key][each]._config.name for each in actualKeys
                    ]
                    expectedValues = [
                        expected[key][each] for each in actualKeys
                    ]
                    self.assert_(
                        0 == len(actualKeySet - expectedKeySet)
                        and 0 == len(expectedKeySet - actualKeySet)
                        and actualValues == expectedValues,
                        "Expected %s %s,\n\nGOT %s"
                        % (
                            key,
                            pprint.pformat(expected[key]),
                            pprint.pformat(actual[key]),
                        ),
                    )
                elif key in [
                    ProcessResults.AFTERBYCONFIG,
                    ProcessResults.BEFOREBYCONFIG,
                ]:
                    actualKeys = actual[key].keys()
                    actualsKeyedByString = {}
                    for stat in actualKeys:
                        actualsKeyedByString[stat._config.name] = actual[key][
                            stat
                        ]
                    actualStringKeySet = set(actualsKeyedByString.keys())
                    expectedKeySet = set(expected[key].keys())
                    self.assert_(
                        0 == len(actualStringKeySet - expectedKeySet)
                        and 0 == len(expectedKeySet - actualStringKeySet),
                        "Expected %s %s,\n\nGOT %s"
                        % (
                            key,
                            pprint.pformat(expected[key]),
                            pprint.pformat(actual[key]),
                        ),
                    )

                    actualValues = [
                        set(actualsKeyedByString[each])
                        for each in actualStringKeySet
                    ]
                    expectedValues = [
                        set(expected[key][each]) for each in actualStringKeySet
                    ]
                    self.assert_(
                        actualValues == expectedValues,
                        "Expected %s %s, got %s"
                        % (key, expected[key], actual[key]),
                    )
                else:
                    self.assert_(
                        False, "Handling not yet implemented for %s" % key
                    )

        # Return back the results in case somebody wants to dive in
        return actual

    def updateProcDefs(
        self,
        procDefs,
        name,
        regex,
        excludeRegex,
        replaceRegex=None,
        replacement=None,
    ):
        procDef = ProcessProxy()
        procDef.name = name
        procDef.includeRegex = regex
        procDef.excludeRegex = excludeRegex
        procDef.replaceRegex = replaceRegex or ".*"
        procDef.replacement = replacement or name
        procDef.primaryUrlPath = "url"
        procDef.generatedId = "url_" + md5(name).hexdigest().strip()
        procDefs[procDef.name] = procDef

    def getProcDefsFrom(self, procDefString):
        """
        Expects a multiline string from a dump of

        python ProcessConfig.py --device=XX

        The string should be trimmed to remove any headers,
        and just contain config output.
        """
        procDefs = {}
        for line in procDefString.split("\n"):
            line = line.strip()
            if line == "":
                continue
            modeler_match, regex, excludeRegex = line.rsplit(None, 2)
            self.updateProcDefs(
                procDefs,
                modeler_match.strip(),
                regex.strip(),
                excludeRegex.strip(),
            )
        return procDefs

    def getProcDefsFromFile(self, procDefFile):
        """
        Expects to read a file that's a dump of

        python ProcessConfig.py --device=XX

        The file should be trimmed to remove any headers,
        and just contain config output.
        """
        base = os.path.join(os.path.dirname(__file__), "zenprocess_data")
        procDefs = {}
        name = base + "/" + procDefFile
        try:
            for line in open(name).readlines():
                procname, regex, excludeRegex = line.rsplit(None, 3)
                self.updateProcDefs(
                    procDefs,
                    procname.strip(),
                    regex.strip(),
                    excludeRegex.strip(),
                )
        except Exception as ex:
            log.warn(
                "Unable to evaluate data file %s because %s", name, str(ex)
            )
        return procDefs

    def getSingleProcessTask(self):
        procDefs = {}
        procName = "url_testProcess_args"
        self.updateProcDefs(
            procDefs, procName, "/fake/path/testProcess", "nothing"
        )
        procDefs["url_testProcess_args"].restart = True
        task = self.makeTask(procDefs)

        # Sanity check our definition with a valid data run
        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/fake/path/testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {".1.3.6.1.2.1.25.4.2.1.5.1": "args"},
        }
        self.compareTestData(data, task, self.expected(PROCESSES=1))

        return task

    def testProcessCount(self):
        task = self.getSingleProcessTask()

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "testProcess",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "testProcess",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "testProcess",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "testProcess",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/fake/path/testProcess",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "/fake/path/testProcess",
                ".1.3.6.1.2.1.25.4.2.1.4.3": "/fake/path/testProcess",
                ".1.3.6.1.2.1.25.4.2.1.4.4": "/fake/path/testProcess",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "1",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "2",
                ".1.3.6.1.2.1.25.4.2.1.5.3": "3",
                ".1.3.6.1.2.1.25.4.2.1.5.4": "4",
            },
        }
        # Process count is not dependent on actual matching,
        # just on the SNMP data returned.
        self.compareTestData(
            data, task, self.expected(PROCESSES=4, AFTERBYCONFIG=1)
        )

    def testMissingNoMatch(self):
        task = self.getSingleProcessTask()

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.9": "otherProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.9": "/non/matching/otherProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {".1.3.6.1.2.1.25.4.2.1.5.9": ""},
        }
        self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingMismatchName(self):
        task = self.getSingleProcessTask()

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "WRONGNAME"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/fake/path/testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {".1.3.6.1.2.1.25.4.2.1.5.1": "args"},
        }
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMissingMismatchNameNoArgs(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs, "url_testProcess1", "testProc", "nothing"
        )
        self.updateProcDefs(
            procDefs, "url_testProcess2", "testProc", "nothing"
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "testProcess1",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "testProcess2",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "testProcess1",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "testProcess2",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "",
            },
        }
        self.compareTestData(
            data, task, self.expected(PROCESSES=2, AFTERBYCONFIG=1, MISSING=1)
        )

    def testMissingMismatchPath(self):
        task = self.getSingleProcessTask()

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/WRONG/PATH"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {".1.3.6.1.2.1.25.4.2.1.5.1": "args"},
        }
        self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingMismatchArgs(self):
        task = self.getSingleProcessTask()

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/fake/path/testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "WRONGARGS"
            },
        }
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMissingMismatchPid(self):
        task = self.getSingleProcessTask()

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.999": "testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.999": "/fake/path/testProcess"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {".1.3.6.1.2.1.25.4.2.1.5.999": "args"},
        }
        self.compareTestData(data, task, self.expected(MISSING=0, RESTARTED=1))

    def testMultipleMissing(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs, "url_testFirst_some", "/fake/path/testFirst", "nothing"
        )
        self.updateProcDefs(
            procDefs, "url_testSecond_args", "/fake/path/testSecond", "nothing"
        )
        self.updateProcDefs(
            procDefs, "url_testThird_went", "/fake/path/testThird", "nothing"
        )
        self.updateProcDefs(
            procDefs, "url_testFourth_here", "/fake/path/testFourth", "nothing"
        )
        self.updateProcDefs(
            procDefs, "url_testFifth_five", "/fake/path/testFifth", "nothing"
        )
        procDefs["url_testFifth_five"].restart = True
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "testFirst",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "testSecond",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "testThird",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "testFourth",
                ".1.3.6.1.2.1.25.4.2.1.2.5": "testFifth",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/fake/path/testFirst",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "/fake/path/testSecond",
                ".1.3.6.1.2.1.25.4.2.1.4.3": "/fake/path/testThird",
                ".1.3.6.1.2.1.25.4.2.1.4.4": "/fake/path/testFourth",
                ".1.3.6.1.2.1.25.4.2.1.4.5": "/fake/path/testFifth",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "some",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "args",
                ".1.3.6.1.2.1.25.4.2.1.5.3": "went",
                ".1.3.6.1.2.1.25.4.2.1.5.4": "here",
                ".1.3.6.1.2.1.25.4.2.1.5.5": "five",
            },
        }
        self.compareTestData(data, task, self.expected(PROCESSES=5, MISSING=0))

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "WRONGPROCESS",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "testSecond",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "testFourth",
                ".1.3.6.1.2.1.25.4.2.1.2.99": "testFifth",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/fake/path/testFirst",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "/fake/path/WRONGPATH",
                ".1.3.6.1.2.1.25.4.2.1.4.4": "/fake/path/testFourth",
                ".1.3.6.1.2.1.25.4.2.1.4.99": "/fake/path/testFifth",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "some",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "args",
                ".1.3.6.1.2.1.25.4.2.1.5.4": "WRONGARGS",
                ".1.3.6.1.2.1.25.4.2.1.5.99": "five",
            },
        }
        self.compareTestData(data, task, self.expected(MISSING=2, RESTARTED=1))

    def testDoubleSendmail(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs, "sendmail_ accepting connections", "sendmail", "nothing"
        )
        self.updateProcDefs(
            procDefs, "sendmail_ something else", "sendmail", "nothing"
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "sendmail: accepting connections",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "sendmail: something else",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "sendmail: accepting connections",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "sendmail: something else",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "",
            },
        }
        self.compareTestData(
            data,
            task,
            self.expected(
                PROCESSES=2, AFTERBYCONFIG=1, MISSING=1, AFTERPIDTOPS=2
            ),
        )

    def testMingetty(self):
        """
        Sanity check for simplified example
        """
        procDefs = {}
        self.updateProcDefs(
            procDefs, "url_mingetty", "/sbin/mingetty", "nothing"
        )
        mingetty = procDefs["url_mingetty"]
        task = self.makeTask(procDefs)

        expectedStats = self.expected(
            PROCESSES=6,
            AFTERBYCONFIG=1,
            AFTERPIDTOPS=6,
            BEFOREBYCONFIG=0,
            NEW=0,
            RESTARTED=0,
            DEAD=0,
            MISSING=0,
        )
        self.compareTestFile("mingetty-0", task, expectedStats)

        # No changes if there are no changes
        # second run of zenprocess --- keeps a history
        # of what was previously monitored
        expectedStats = self.expected(
            PROCESSES=6,
            AFTERBYCONFIG=1,
            AFTERPIDTOPS=6,
            BEFOREBYCONFIG=1,
            NEW=0,
            RESTARTED=0,
            DEAD=0,
            MISSING=0,
        )
        self.compareTestFile("mingetty-0", task, expectedStats)

        # Note: the restart count is only used if we want to
        #       receive notifications
        expectedStats = self.expected(
            PROCESSES=6,
            AFTERBYCONFIG=1,
            AFTERPIDTOPS=6,
            BEFOREBYCONFIG=1,
            NEW=0,
            RESTARTED=0,
            DEAD=0,
            MISSING=0,
        )
        self.compareTestFile("mingetty-1", task, expectedStats)

        mingetty.restart = True
        expectedStats = self.expected(
            PROCESSES=6,
            AFTERBYCONFIG=1,
            AFTERPIDTOPS=6,
            BEFOREBYCONFIG=1,
            NEW=0,
            RESTARTED=1,
            DEAD=0,
            MISSING=0,
        )
        self.compareTestFile("mingetty-0", task, expectedStats)

    def pprintProcStats(self, actual, prefix):
        # resultKeys = (
        #     AFTERBYCONFIG, AFTERPIDTOPS, BEFOREBYCONFIG, NEW,
        #     RESTARTED, DEAD, MISSING,
        # )
        print()
        print("%s = {}" % prefix)
        print()
        print(
            "%s['%s'] = %s"
            % (
                prefix,
                ProcessResults.AFTERBYCONFIG,
                pprint.pformat(actual[ProcessResults.AFTERBYCONFIG]),
            )
        )
        print()
        print(
            "%s['%s'] = %s"
            % (
                prefix,
                ProcessResults.AFTERPIDTOPS,
                pprint.pformat(actual[ProcessResults.AFTERPIDTOPS]),
            )
        )
        print()
        print(
            "%s['%s'] = %s"
            % (
                prefix,
                ProcessResults.BEFOREBYCONFIG,
                pprint.pformat(actual[ProcessResults.BEFOREBYCONFIG]),
            )
        )
        print()
        print(
            "%s['%s'] = %s"
            % (prefix, ProcessResults.NEW, actual[ProcessResults.NEW])
        )
        print()
        print(
            "%s['%s'] = %s"
            % (
                prefix,
                ProcessResults.RESTARTED,
                pprint.pformat(actual[ProcessResults.RESTARTED]),
            )
        )
        print()
        print(
            "%s['%s'] = %s"
            % (prefix, ProcessResults.DEAD, actual[ProcessResults.DEAD])
        )
        print()
        print(
            "%s['%s'] = %s"
            % (
                prefix,
                ProcessResults.MISSING,
                pprint.pformat(
                    ["%s" % each for each in actual[ProcessResults.MISSING]]
                ),
            )
        )

    def testRemodels(self):
        """names only from "diff remodel_bug-0 remodel_bug-1" :
        119,120d118
        <                             '.1.3.6.1.2.1.25.4.2.1.2.6945': 'bash',
        <                             '.1.3.6.1.2.1.25.4.2.1.2.6948': 'python',
        128,129c126,127
        <                             '.1.3.6.1.2.1.25.4.2.1.2.8450': 'python',
        <                             '.1.3.6.1.2.1.25.4.2.1.2.8470': 'python',
        ---
        >                             '.1.3.6.1.2.1.25.4.2.1.2.8478': 'vim',
        """
        procDefs = {}
        self.updateProcDefs(procDefs, "url_python", "python", "nothing")
        self.updateProcDefs(
            procDefs, "url_java", ".*zeneventserver.*", "nothing"
        )
        task = self.makeTask(procDefs)

        expectedStats = self.expected(
            PROCESSES=135,
            AFTERBYCONFIG={
                "url_python": [
                    1004,
                    32073,
                    32075,
                    32076,
                    3736,
                    6948,
                    8447,
                    8450,
                    8470,
                ],
                "url_java": [31948],
            },
            AFTERPIDTOPS={
                1004: "url_python",
                3736: "url_python",
                6948: "url_python",
                31948: "url_java",
                32073: "url_python",
                32075: "url_python",
                32076: "url_python",
                8447: "url_python",
                8450: "url_python",
                8470: "url_python",
            },
            BEFOREBYCONFIG={},
            NEW=set(),
            RESTARTED=0,
            DEAD=set(),
            MISSING=[],
        )

        self.compareTestFile("remodel_bug-0", task, expectedStats)

        procDefs = {}
        self.updateProcDefs(procDefs, "url_python", "python", "nothing")
        self.updateProcDefs(
            procDefs, "url_java", ".*zeneventserver.*", "nothing"
        )
        self.updateProcDefs(
            procDefs, "url_vim", ".*zenprocess.py.*", "nothing"
        )

        expectedStats = self.expected(
            PROCESSES=132,
            AFTERBYCONFIG={
                "url_python": [1004, 32073, 32075, 32076, 3736, 8447],
                "url_java": [31948],
                "url_vim": [8478],
            },
            AFTERPIDTOPS={
                1004: "url_python",
                3736: "url_python",
                8447: "url_python",
                8478: "url_vim",
                31948: "url_java",
                32073: "url_python",
                32075: "url_python",
                32076: "url_python",
            },
            BEFOREBYCONFIG={
                "url_python": [
                    1004,
                    32073,
                    32075,
                    32076,
                    3736,
                    6948,
                    8447,
                    8450,
                    8470,
                ],
                "url_java": [31948],
            },
            NEW={8478},
            RESTARTED=0,
            DEAD={6948, 8450, 8470},
            MISSING=[],
        )
        config = TaskConfig(procDefs=procDefs)
        task._deviceStats.update(config)
        self.compareTestFile("remodel_bug-1", task, expectedStats)

    def testSubsetCorrectMatch(self):
        procDefs = {}
        self.updateProcDefs(procDefs, "url_rpciod_3", "rpc", "nothing")
        self.updateProcDefs(procDefs, "url_rpciod_32", "rpc", "nothing")
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "rpciod/3",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "rpciod/32",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "rpciod/3",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "rpciod/32",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "",
            },
        }

        self.compareTestData(
            data, task, self.expected(PROCESSES=2, AFTERBYCONFIG=1, MISSING=1)
        )

    def testSuffixCorrectMatch(self):
        procDefs = {}
        self.updateProcDefs(procDefs, "url_iod_3", "iod", "nothing")
        self.updateProcDefs(procDefs, "url_ciod_3", "iod", "nothing")
        self.updateProcDefs(procDefs, "url_pciod_3", "iod", "nothing")
        self.updateProcDefs(procDefs, "url_rpciod_3", "iod", "nothing")
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "iod/3",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "ciod/3",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "pciod/3",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "rpciod/3",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/etc/iod/3",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "/etc/ciod/3",
                ".1.3.6.1.2.1.25.4.2.1.4.3": "/etc/pciod/3",
                ".1.3.6.1.2.1.25.4.2.1.4.4": "/etc/rpciod/3",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "",
                ".1.3.6.1.2.1.25.4.2.1.5.3": "",
                ".1.3.6.1.2.1.25.4.2.1.5.4": "",
            },
        }

        self.compareTestData(
            data, task, self.expected(PROCESSES=4, AFTERBYCONFIG=1, MISSING=3)
        )

    def testRpciods(self):
        procDefs = {}
        self.updateProcDefs(procDefs, "url_rpciod_0", "rpc", "nothing")
        task = self.makeTask(procDefs)
        self.compareTestFile(
            "rpciod_test",
            task,
            self.expected(PROCESSES=33, AFTERBYCONFIG=1, NEW=0, MISSING=0),
        )

    def testSpecialCharacterSuffix(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs,
            "url_sendmail_accepting_connections",
            "sendmail",
            "nothing",
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "sendmail: accepting connections"
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "sendmail: accepting connections"
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {".1.3.6.1.2.1.25.4.2.1.5.1": ""},
        }

        self.compareTestData(
            data, task, self.expected(PROCESSES=1, AFTERBYCONFIG=1, MISSING=0)
        )

    def testCase3776(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs,
            "pyres_manager",
            r"pyres_manager: running \['pmta'\]",
            "nothing",
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "pyres_manager: running ['pmta']",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "pyres_manager: running ['pmta']",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "",
            },
        }

        self.compareTestData(
            data,
            task,
            self.expected(
                PROCESSES=1, AFTERBYCONFIG=1, MISSING=0, AFTERPIDTOPS=1
            ),
        )

    def testSingleExcludeRegex(self):
        procDefs = {}
        self.updateProcDefs(procDefs, "url_process1", "proc", ".*process.*")
        self.updateProcDefs(
            procDefs, "url_proc2", "doesntMatter", "doesntMatter"
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "name1",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "name2",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/path/to/process1",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "/path/to/process2",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "arbitrary arguments",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "arbitrary arguments",
            },
        }

        self.compareTestData(
            data, task, self.expected(PROCESSES=2, AFTERBYCONFIG=0, MISSING=2)
        )

    def testMultipleExcludeRegex(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs,
            "url_myapp1",
            ".*myapp.*",
            ".*(vim|tail|grep|tar|cat|bash).*",
        )
        self.updateProcDefs(
            procDefs, "url_myapp2", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp3", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp4", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp5", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp6", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp7", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp8", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp9", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp10", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp11", "doesntMatter", "doesntMatter"
        )
        self.updateProcDefs(
            procDefs, "url_myapp12", "doesntMatter", "doesntMatter"
        )
        task = self.makeTask(procDefs)

        """
        1.  myapp                               #legitimate
        2.  vim myapp
        3.  vim /path/to/myapp
        4.  tail -f myapp.log
        5.  tail -f /path/to/myapp.log
        6.  /path/to/myapp                      #legitimate
        7.  grep foo myapp
        8.  grep foo /path/to/myapp
        9.  tar cvfz bar.tgz /path/to/myapp
        10. cat /path/to/myapp
        11. bash -c "/path/to/myapp"
        12. bash -c myapp
        """

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "myapp",  # legitimate
                ".1.3.6.1.2.1.25.4.2.1.2.2": "vim",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "vim",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "tail",
                ".1.3.6.1.2.1.25.4.2.1.2.5": "tail",
                ".1.3.6.1.2.1.25.4.2.1.2.6": "myapp",  # legitimate
                ".1.3.6.1.2.1.25.4.2.1.2.7": "grep",
                ".1.3.6.1.2.1.25.4.2.1.2.8": "grep",
                ".1.3.6.1.2.1.25.4.2.1.2.9": "tar",
                ".1.3.6.1.2.1.25.4.2.1.2.10": "cat",
                ".1.3.6.1.2.1.25.4.2.1.2.11": "bash",
                ".1.3.6.1.2.1.25.4.2.1.2.12": "bash",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "myapp",  # legitimate
                ".1.3.6.1.2.1.25.4.2.1.2.2": "vim",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "vim",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "tail",
                ".1.3.6.1.2.1.25.4.2.1.2.5": "tail",
                ".1.3.6.1.2.1.25.4.2.1.2.6": "/path/to/myapp",  # legitimate
                ".1.3.6.1.2.1.25.4.2.1.2.7": "grep",
                ".1.3.6.1.2.1.25.4.2.1.2.8": "grep",
                ".1.3.6.1.2.1.25.4.2.1.2.9": "tar",
                ".1.3.6.1.2.1.25.4.2.1.2.10": "cat",
                ".1.3.6.1.2.1.25.4.2.1.2.11": "bash",
                ".1.3.6.1.2.1.25.4.2.1.2.12": "bash",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "",  # legitimate
                ".1.3.6.1.2.1.25.4.2.1.5.2": "myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "/path/to/myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "-f myapp.log",
                ".1.3.6.1.2.1.25.4.2.1.2.5": "-f /path/to/myapp.log",
                ".1.3.6.1.2.1.25.4.2.1.2.6": "",  # legitimate
                ".1.3.6.1.2.1.25.4.2.1.2.7": "foo myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.8": "foo /path/to/myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.9": "cvfz bar.tgz /path/to/myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.10": "/path/to/myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.11": '-c "/path/to/myapp"',
                ".1.3.6.1.2.1.25.4.2.1.2.12": "-c myapp",
            },
        }
        expectedStats = self.expected(
            PROCESSES=12,
            AFTERBYCONFIG={"url_myapp1": [1, 6]},
            AFTERPIDTOPS={
                1: "url_myapp1",
                6: "url_myapp1",
            },
            MISSING=11,
        )

        self.compareTestData(data, task, expectedStats)

    def testSingleNameCaptureGroupSingleProcesses(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs,
            "myapp",
            r"myapp[^\/]*\/",
            "nothing",
            r".*(myapp[^\/]*)\/.*",
            "\\1",
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {".1.3.6.1.2.1.25.4.2.1.2.1": "myapp"},
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": (
                    "/home/zenoss/dummy_processes/myapp/somedir/myapp"
                ),
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "arbitrary arguments"
            },
        }

        self.compareTestData(
            data, task, self.expected(PROCESSES=1, AFTERBYCONFIG=1, MISSING=0)
        )

    def testSingleNameCaptureGroupMultipleProcesses(self):
        procDefs = {}
        self.updateProcDefs(
            procDefs,
            "myapp",
            r"myapp[^\/]*\/",
            "nothing",
            r".*(myapp[^\/]*)\/.*",
            "\\1",
        )
        self.updateProcDefs(
            procDefs,
            "myappiscool",
            r"myapp[^\/]*\/",
            "nothing",
            r".*(myapp[^\/]*)\/.*",
            "\\1",
        )
        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "otherapp",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": (
                    "/home/zenoss/dummy_processes/myapp/somedir/myapp"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.2": (
                    "/home/zenoss/dummy_processes/myappiscool/otherapp"
                ),
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "arbitrary arguments",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "arbitrary arguments",
            },
        }

        self.compareTestData(
            data, task, self.expected(PROCESSES=2, AFTERBYCONFIG=2, MISSING=0)
        )

    def testMultipleNameCaptureGroupsMultipleProcesses(self):
        procDefs = {}

        self.updateProcDefs(
            procDefs,
            "television_celtic",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "television_celery",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "television_cellular_phones",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "telephone_celtic",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "telephone_celery",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "telephone_cellular_phones",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "telekinesis_celtic",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "telekinesis_celery",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )
        self.updateProcDefs(
            procDefs,
            "telekinesis_cellular_phones",
            r"tele[^\/]*\/.*cel[^\/]*\/",
            "nothing",
            r".*(tele[^\/]*)\/.*(cel[^\/]*)\/.*",
            "\\1_\\2",
        )

        task = self.makeTask(procDefs)

        data = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.3": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.4": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.5": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.6": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.7": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.8": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.9": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.10": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.11": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.12": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.13": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.14": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.15": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.16": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.17": "telecel",
                ".1.3.6.1.2.1.25.4.2.1.2.18": "telecel",
            },
            ".1.3.6.1.2.1.25.4.2.1.2.1": "telecel",
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/television/folder1"
                    "/celtic/test1.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.2": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/television/folder1"
                    "/celtic/test11.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.3": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/television/folder1"
                    "/celery/test2.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.4": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/television/folder1"
                    "/celery/test22.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.5": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/television/folder1"
                    "/cellular_phones/test3.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.6": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/television/folder1"
                    "/cellular_phones/test33.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.7": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telephone/folder1"
                    "/celtic/test1.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.8": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telephone/folder1"
                    "/celtic/test11.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.9": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telephone/folder1"
                    "/celery/test2.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.10": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telephone/folder1"
                    "/celery/test22.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.11": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telephone/folder1"
                    "/cellular_phones/test3.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.12": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telephone/folder1"
                    "/cellular_phones/test33.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.13": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telekinesis/folder1"
                    "/celtic/test1.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.14": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telekinesis/folder1"
                    "/celtic/test11.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.15": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telekinesis/folder1"
                    "/celery/test2.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.16": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telekinesis/folder1"
                    "/celery/test22.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.17": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telekinesis/folder1"
                    "/cellular_phones/test3.sh"
                ),
                ".1.3.6.1.2.1.25.4.2.1.4.18": (
                    "/home/zenoss/dummy_processes"
                    "/test_two_name_capture_groups/telekinesis/folder1"
                    "/cellular_phones/test33.sh"
                ),
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "arbitrary arguments",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "arbitrary arguments",
            },
        }
        self.compareTestData(
            data, task, self.expected(PROCESSES=18, AFTERBYCONFIG=9, MISSING=0)
        )

    def testMapResultsToDicts(self):
        values = {
            ".1.3.6.1.2.1.25.4.2.1.2": {
                ".1.3.6.1.2.1.25.4.2.1.2.1": "myapp",
                ".1.3.6.1.2.1.25.4.2.1.2.2": "otherapp",
            },
            ".1.3.6.1.2.1.25.4.2.1.4": {
                ".1.3.6.1.2.1.25.4.2.1.4.1": "/dummy_processes/myapp",
                ".1.3.6.1.2.1.25.4.2.1.4.2": "/dummy_processes/otherapp",
            },
            ".1.3.6.1.2.1.25.4.2.1.5": {
                ".1.3.6.1.2.1.25.4.2.1.5.1": "arbitrary arguments",
                ".1.3.6.1.2.1.25.4.2.1.5.2": "arbitrary arguments",
            },
        }

        result = mapResultsToDicts(False, values)

        expected = [
            (1, "/dummy_processes/myapp arbitrary arguments"),
            (2, "/dummy_processes/otherapp arbitrary arguments"),
        ]

        self.assertEqual(result, expected)


def test_suite():
    from unittest import TestSuite, makeSuite

    # TestSuite - aggregate of individual test cases/suites
    suite = TestSuite()

    # makeSuite - Returns a suite with one instance of TestZenProcess
    # for each method starting with the word 'test'
    testSuite = makeSuite(TestZenprocess)

    # addTest - Add a TestCase or TestSuite to the suite
    suite.addTest(testSuite)

    return suite
