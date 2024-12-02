##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from md5 import md5
from pprint import pformat

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD.parsers.ps import ps, resetRecentlySeenPids

# Disable logging to stdout (or anywhere else)
rootLogger = logging.getLogger()
rootLogger.handlers = []
handler = logging.NullHandler()
rootLogger.addHandler(handler)


class Object(object):
    def __init__(self, **kw):
        for k, v in kw.iteritems():
            setattr(self, k, v)

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return pformat(
            dict(
                (attr, getattr(self, attr))
                for attr in dir(self)
                if not attr.startswith("__")
            )
        )


def _getDatapoint(data, name):
    """ """
    return next(((dp, v) for dp, v in data if dp["id"] == name), (None, None))


class TestBasicPSParsing(BaseTestCase):
    """ """

    def setUp(self):
        self.cmd = Object(
            **{
                "deviceConfig": Object(
                    **{"device": "localhost", "lastmodeltime": "lastmodeltime"}
                ),
                "command": "command",
                "includeRegex": ".*Job.*",
                "excludeRegex": "nothing",
                "replaceRegex": ".*",
                "replacement": "Job",
                "primaryUrlPath": "url",
                "displayName": "Job",
                "eventKey": "bar",
                "severity": 3,
                "generatedId": "url_" + md5("Job").hexdigest().strip(),
                "points": [
                    Object(
                        **{
                            "id": "cpu",
                            "data": {
                                "id": "url_Job",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                    Object(
                        **{
                            "id": "mem",
                            "data": {
                                "id": "url_Job",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                    Object(
                        **{
                            "id": "count",
                            "data": {
                                "id": "url_Job",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                ],
            }
        )
        self.cmd.result = Object(**{"exitCode": 0})
        resetRecentlySeenPids()

    def tearDown(self):
        self.cmd = None
        del self.cmd

    def test_dataForParser(self):
        """Verifies that the dataForParser method on the ps object
        returns the expected result.
        """
        parser = ps()
        ctx = type(
            "Context",
            (object,),
            {"getOSProcessConf": lambda x: ("someId", True, 3)},
        )()
        data = parser.dataForParser(ctx, "unused")
        expected = {"id": "someId", "alertOnRestart": True, "failSeverity": 3}
        self.assertEqual(data, expected)

    def test_DatapointsProcessed(self):
        """Verifies that the processResults method populates the second
        argument ('results') with the expected values.
        """
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 00:00:30 someJob a b c",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.events), 1)

        event = results.events[0]
        self.assertEqual(event.get("component"), "Job")
        self.assertEqual(event.get("eventGroup"), "Process")
        self.assertEqual(event.get("eventClass"), "/Status/OSProcess")
        self.assertEqual(event.get("severity"), 0)

        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        mem, memValue = _getDatapoint(results.values, "mem")
        count, countValue = _getDatapoint(results.values, "count")

        self.assertIsNotNone(cpu)
        self.assertIsNotNone(mem)
        self.assertIsNotNone(count)

        self.assertEqual(cpuValue, 30)
        self.assertEqual(memValue, 1024)
        self.assertEqual(countValue, 1)

    def test_parsesShortTimestamp(self):
        """Verifies that abbreviated timestamps are parsed correctly."""
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 10:23 notherJob1 a b c",
            )
        )
        results = ParsedResults()
        parser = ps()
        parser.processResults(self.cmd, results)
        cpuTime = next(
            (v for dp, v in results.values if dp["id"] == "cpu"), None
        )
        self.assertEqual(cpuTime, 623)

    def test_resultEvents(self):
        """Verifies the content and quantity of events in the result."""
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 10:23 notherJob1 a b c",
                "123 1 00:05:01 someJob a b c",
                "657 1 2-03:00:00 someJob a b c",
                "8766 1 00:10:00 unrelatedTask a b c",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)
        self.assertEqual(len(results.events), 3)
        for event in results.events:
            self.assertEqual(event.get("component"), "Job")
            self.assertEqual(event.get("eventGroup"), "Process")
            self.assertEqual(event.get("eventClass"), "/Status/OSProcess")
            self.assertEqual(event.get("severity"), 0)

    def test_sumsCpuTimes(self):
        """Verifies that the CPU times of multiple instances of the same
        process are summed together.
        """
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 10:23 notherJob1 a b c",
                "123 1 00:05:01 someJob a b c",
                "657 1 2-03:00:00 someJob a b c",
                "8766 1 00:10:00 unrelatedTask a b c",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)
        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertEqual(cpuValue, 184524)

    def test_sumsMemory(self):
        """Verifies that the memory usage of multiple instances of the same
        process are summed together.
        """
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 10:23 notherJob1 a b c",
                "123 1 00:05:01 someJob a b c",
                "657 1 2-03:00:00 someJob a b c",
                "8766 1 00:10:00 unrelatedTask a b c",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)
        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertEqual(memValue, 3072)

    def test_countsProcesses(self):
        """Verifies that the count of multiple instances of the same
        process is correct.
        """
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 10:23 notherJob1 a b c",
                "123 1 00:05:01 someJob a b c",
                "657 1 2-03:00:00 someJob a b c",
                "8766 1 00:10:00 unrelatedTask a b c",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)
        count, countValue = _getDatapoint(results.values, "count")
        self.assertEqual(countValue, 3)

    def test_NoResultsOnFailure(self):
        """If the ps command has a non-zero exit code, disregard the output.
        The result is a missed collection.
        """
        self.cmd.result.exitCode = 1
        self.cmd.result.output = "\n".join(())
        results = ParsedResults()
        ps().processResults(self.cmd, results)
        self.assertEqual(len(results.values), 0)
        self.assertEqual(len(results.events), 0)


class TestMultipleCollections(BaseTestCase):
    """Test case for multiple collections."""

    def setUp(self):
        self.cmd = Object(
            **{
                "deviceConfig": Object(
                    **{"device": "localhost", "lastmodeltime": "lastmodeltime"}
                ),
                "command": "command",
                "includeRegex": ".*Job.*",
                "excludeRegex": "nothing",
                "replaceRegex": ".*",
                "replacement": "Job",
                "primaryUrlPath": "url",
                "displayName": "Job",
                "eventKey": "bar",
                "severity": 3,
                "generatedId": "url_" + md5("Job").hexdigest().strip(),
                "points": [
                    Object(
                        **{
                            "id": "cpu",
                            "data": {
                                "id": "url_Job",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                    Object(
                        **{
                            "id": "mem",
                            "data": {
                                "id": "url_Job",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                    Object(
                        **{
                            "id": "count",
                            "data": {
                                "id": "url_Job",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                ],
            }
        )
        self.cmd.result = Object(**{"exitCode": 0})

    def tearDown(self):
        self.cmd = None
        del self.cmd

    def test_collectionSteps(self):
        """Verifies that data captured in the first collection is
        used in the second collection correctly.
        """
        # First collection
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "345 1 10:23 extraJob a b c",
                "123 1 00:00:00 someJob a b c",
                "234 1 00:00:00 anotherJob a b c",
            )
        )
        ps().processResults(self.cmd, ParsedResults())

        # Reset 'result' for second collection
        self.cmd.result = Object(**{"exitCode": 0})
        self.step_changedProcesses()

        # Reset 'result' for third collection
        self.cmd.result = Object(**{"exitCode": 0})
        self.step_processDown()

        # Reset 'result' for third collection
        self.cmd.result = Object(**{"exitCode": 0})
        self.step_processReturns()

    def step_changedProcesses(self):
        """Verifies that a changed process set is handled correctly."""
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "124 1 00:00:00 someJob a b c",
                "456 1 00:00:00 someOtherJob 1 2 3",
            )
        )

        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 0)

        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertIsNotNone(mem)
        self.assertEqual(memValue, 2048)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertIsNotNone(count)
        self.assertEqual(countValue, 2)

        self.assertEqual(len(results.events), 1)

        event = results.events[0]

        self.assertEqual(event.get("severity"), 3)

        message = event.get("message", "")

        begin = message.find("[") + 1
        end = message.find("]", begin)
        discardedPids = [p.strip() for p in message[begin:end].split(",")]

        begin = message.find("[", end + 1) + 1
        end = message.find("]", begin)
        newPids = [p.strip() for p in message[begin:end].split(",")]

        self.assertSetEqual(set(discardedPids), set(["345", "123", "234"]))
        self.assertSetEqual(set(newPids), set(["124", "456"]))

    def step_processDown(self):
        """Verifies that an 'empty' process set is handled correctly."""
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "124 1 00:00:00 unrelatedTask a b c",
                "782 1 00:00:00 anotherUnrelatedTask 1 2 3",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 1)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertEqual(countValue, 0)

        self.assertEqual(len(results.events), 1)

        event = results.events[0]
        self.assertEqual(event.get("component"), "Job")
        self.assertEqual(event.get("eventGroup"), "Process")
        self.assertEqual(event.get("eventClass"), "/Status/OSProcess")
        self.assertEqual(event.get("severity"), 3)

    def step_processReturns(self):
        """Verifies that a 'repopulated' process set is handled correctly."""
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "124 1 00:00:00 someJob a b c",
                "456 1 00:00:00 someOtherJob 1 2 3",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)
        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 0)

        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertIsNotNone(mem)
        self.assertEqual(memValue, 2048)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertIsNotNone(count)
        self.assertEqual(countValue, 2)

        self.assertEqual(len(results.events), 2)
        self.assertTrue(all(e["severity"] == 0 for e in results.events))
        self.assertTrue(all(e["component"] == "Job" for e in results.events))
        self.assertTrue(
            all(e["eventGroup"] == "Process" for e in results.events)
        )
        self.assertTrue(
            all(e["eventClass"] == "/Status/OSProcess" for e in results.events)
        )


class TestEdgeCases(BaseTestCase):
    """Test case for possible edge cases."""

    def setUp(self):
        self.cmd = Object(
            **{
                "deviceConfig": Object(
                    **{"device": "localhost", "lastmodeltime": "lastmodeltime"}
                ),
                "command": "command",
                "includeRegex": ".*oracle.*",
                "excludeRegex": "nothing",
                "replaceRegex": ".*",
                "replacement": "sendmail",
                "primaryUrlPath": "url",
                "displayName": "Oracle process set",
                "eventKey": "bar",
                "severity": 1,
                "generatedId": "url_" + md5("sendmail").hexdigest().strip(),
                "points": [
                    Object(
                        **{
                            "id": "cpu_cpu",
                            "data": {
                                "id": "url_oracle",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    )
                ],
            }
        )
        self.cmd.result = Object(**{"exitCode": 0})
        resetRecentlySeenPids()

    def tearDown(self):
        self.cmd = None
        del self.cmd

    def test_ignoresParenthesis(self):
        """Verify that parenthesis don't disrupt process detection."""
        self.cmd.result.output = "\n".join(
            (
                " PID   RSS        TIME COMMAND",
                "483362 146300  22:58:11 /opt/test/oracleYAMDB1 (LOCAL=NO)",
                "495844 137916  22:45:57 /bin/sendmail: accepting connections",
                "520290  1808   00:00:00 /sbin/aixmibd",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 1)
        cpu, cpuValue = _getDatapoint(results.values, "cpu_cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 82691)

        self.assertEqual(len(results.events), 1)
        event = results.events[0]
        self.assertIn("Process up", event.get("summary", ""))


class TestDefunctProcesses(BaseTestCase):
    def setUp(self):
        self.cmd = Object(
            **{
                "deviceConfig": Object(
                    **{"device": "localhost", "lastmodeltime": "lastmodeltime"}
                ),
                "command": "command",
                "includeRegex": ".*defunct.*",
                "excludeRegex": "nothing",
                "replaceRegex": ".*",
                "replacement": "defunct",
                "primaryUrlPath": "url",
                "displayName": "defunct process set",
                "eventKey": "bar",
                "severity": 1,
                "generatedId": "url_" + md5("defunct").hexdigest().strip(),
                "points": [
                    Object(
                        **{
                            "id": "cpu_cpu",
                            "data": {
                                "id": "url_defunct",
                                "alertOnRestart": False,
                                "failSeverity": 0,
                            },
                        }
                    )
                ],
            }
        )
        self.cmd.result = Object(**{"exitCode": 0})

    def tearDown(self):
        self.cmd = None
        del self.cmd

    def test_defuncts(self):
        """ """
        self.cmd.result.output = "\n".join(
            (
                " PID   RSS        TIME COMMAND",
                "288 00:00:00 <defunct>",
                "289 1788 00:00:00 sshd: root@sherwood",
                "294 448 00:00:08 aioserver",
                "296 00:00:00 <defunct>",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 1)
        self.assertEqual(len(results.events), 0)

        # Reset 'result' for second collection
        self.cmd.result = Object(**{"exitCode": 0})
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "288 00:00:00 <defunct>",
                "296 00:00:00 <defunct>",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 1)

        self.assertEqual(len(results.events), 2)
        event1, event2 = results.events

        self.assertIn("Process up", event1.get("summary", ""))
        self.assertIn("Process up", event2.get("summary", ""))

        self.assertIn("defunct", event1.get("summary", ""))
        self.assertIn("defunct", event2.get("summary", ""))

        self.assertEqual(event1.get("severity"), 0)
        self.assertEqual(event2.get("severity"), 0)


class TestCmdConfigs(BaseTestCase):
    def setUp(self):
        self.cmd = Object(
            **{
                "deviceConfig": Object(
                    **{"device": "localhost", "lastmodeltime": "a second ago"}
                ),
                "command": "command",
                "includeRegex": "",
                "excludeRegex": "",
                "replaceRegex": "",
                "replacement": "myapp",
                "primaryUrlPath": "url",
                "displayName": "myapp process set",
                "eventKey": "bar",
                "severity": 1,
                "generatedId": "url_" + md5("myapp").hexdigest().strip(),
                "points": [
                    Object(
                        **{
                            "id": "cpu",
                            "data": {
                                "id": "url_myapp",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                    Object(
                        **{
                            "id": "mem",
                            "data": {
                                "id": "url_myapp",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                    Object(
                        **{
                            "id": "count",
                            "data": {
                                "id": "url_myapp",
                                "alertOnRestart": True,
                                "failSeverity": 3,
                            },
                        }
                    ),
                ],
            }
        )
        self.cmd.result = Object(**{"exitCode": 0})
        resetRecentlySeenPids()

    def tearDown(self):
        self.cmd = None
        del self.cmd

    def test_excludeRegex(self):
        """ """
        self.cmd.includeRegex = ".*myapp.*"
        self.cmd.excludeRegex = ".*(vim|tail|grep|tar|cat|bash).*"
        self.cmd.replaceRegex = ".*"

        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "120 1 00:00:01 myapp",
                "121 1 00:00:02 vim myapp",
                "122 1 00:00:03 vim /path/to/myapp",
                "123 1 00:00:04 tail -f myapp.log",
                "124 1 00:00:05 tail -f /path/to/myapp.log",
                "125 1 00:00:06 /path/to/myapp",
                "126 1 00:00:07 grep foo myapp",
                "127 1 00:00:08 grep foo /path/to/myapp",
                "128 1 00:00:09 tar cvfz bar.tgz /path/to/myapp",
                "129 1 00:00:10 tar cvfz bar.tgz /path/to/myapp",
                "130 1 00:00:11 cat /path/to/myapp",
                "131 1 00:00:12 bash -c /path/to/myapp",
                "132 1 00:00:13 bash -c myapp",
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 7.0)

        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertIsNotNone(mem)
        self.assertEqual(memValue, 2048.0)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertIsNotNone(count)
        self.assertEqual(countValue, 2)

        self.assertEqual(len(results.events), 2)
        self.assertTrue(
            all("Process up" in ev.get("summary", "") for ev in results.events)
        )

        # Reset 'result' for second collection
        self.cmd.result = Object(**{"exitCode": 0})
        results = ParsedResults()
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "120 1 00:00:01 myapp",
                "125 1 00:00:06 /path/to/myapp",
            )
        )
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 7.0)

        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertIsNotNone(mem)
        self.assertEqual(memValue, 2048.0)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertIsNotNone(count)
        self.assertEqual(countValue, 2)

        self.assertEqual(len(results.events), 2)
        self.assertTrue(
            all("Process up" in ev.get("summary", "") for ev in results.events)
        )

    def test_matchOnGeneratedId(self):
        """
        test the include and replace regex fields
        """
        self.cmd.includeRegex = r"tele.[^\/]*\/.*cel[^\/].*\/"
        self.cmd.excludeRegex = "nothing"
        self.cmd.replaceRegex = r".*(tele.[^\/]*)\/.*(cel[^\/].*)\/.*"
        self.cmd.replacement = "\\1_\\2"
        self.cmd.displayName = "NCGs"
        self.cmd.generatedId = (
            "url_" + md5("telekinesis_celery").hexdigest().strip()
        )

        self.step_regexCaptureGroups_1()
        self.cmd.result = Object(**{"exitCode": 0})
        self.step_regexCaptureGroups_2()

    def step_regexCaptureGroups_1(self):
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "120 1 00:00:01 /opt/television/src/celtic/test1.sh",
                "121 1 00:00:02 /opt/television/src/celtic/test11.sh",
                "122 1 00:00:03 /opt/television/src/celery/test2.sh",
                "123 1 00:00:04 /opt/television/src/celery/test22.sh",
                "124 1 00:00:05 /opt/television/src/cellular_phones/test3.sh",
                "125 1 00:00:06 /opt/television/src/cellular_phones/test33.sh",
                "126 1 00:00:07 /opt/telephone/src/celtic/test1.sh",
                "127 1 00:00:08 /opt/telephone/src/celtic/test11.sh",
                "128 1 00:00:09 /opt/telephone/src/celery/test2.sh",
                "129 1 00:00:10 /opt/telephone/src/celery/test22.sh",
                "130 1 00:00:11 /opt/telephone/src/cellular_phones/test3.sh",
                "131 1 00:00:12 /opt/telephone/src/cellular_phones/test33.sh",
                "132 1 00:00:13 /opt/telekinesis/src/celtic/test1.sh",
                "133 1 00:00:14 /opt/telekinesis/src/celtic/test11.sh",
                "134 1 00:00:15 /opt/telekinesis/src/celery/test2.sh",
                "135 1 00:00:16 /opt/telekinesis/src/celery/test22.sh",
                "136 1 00:00:17 /opt/telekinesis/src/cellular_phones/test3.sh",
                "137 1 00:00:18 /opt/telekinesis/src/cellular_phones/test33.sh",  # noqa E501
            )
        )
        results = ParsedResults()
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 31)

        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertIsNotNone(mem)
        self.assertEqual(memValue, 2 * 1024.0)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertIsNotNone(count)
        self.assertEqual(countValue, 2)

        self.assertEqual(len(results.events), 2)
        self.assertTrue(
            all("Process up" in ev.get("summary", "") for ev in results.events)
        )

    def step_regexCaptureGroups_2(self):
        # Reset 'result' for second collection
        results = ParsedResults()
        self.cmd.result.output = "\n".join(
            (
                "  PID   RSS     TIME COMMAND",
                "120 1 00:00:01 /opt/television/src/celtic/test1.sh",
                "121 1 00:00:02 /opt/television/src/celtic/test11.sh",
                "122 1 00:00:03 /opt/television/src/celery/test2.sh",
                "123 1 00:00:04 /opt/television/src/celery/test22.sh",
                "124 1 00:00:05 /opt/television/src/cellular_phones/test3.sh",
                "125 1 00:00:06 /opt/television/src/cellular_phones/test33.sh",
                "126 1 00:00:07 /opt/telephone/src/celtic/test1.sh",
                "127 1 00:00:08 /opt/telephone/src/celtic/test11.sh",
                "128 1 00:00:09 /opt/telephone/src/celery/test2.sh",
                "129 1 00:00:10 /opt/telephone/src/celery/test22.sh",
                "130 1 00:00:11 /opt/telephone/src/cellular_phones/test3.sh",
                "131 1 00:00:12 /opt/telephone/src/cellular_phones/test33.sh",
                "132 1 00:00:13 /opt/telekinesis/src/celtic/test1.sh",
                "133 1 00:00:14 /opt/telekinesis/src/celtic/test11.sh",
                "134 1 00:00:15 /opt/telekinesis/src/celery/test2.sh",
                "135 1 00:00:16 /opt/telekinesis/src/celery/test22.sh",
                "136 1 00:00:17 /opt/telekinesis/src/cellular_phones/test3.sh",
                "137 1 00:00:18 /opt/telekinesis/src/cellular_phones/test33.sh",  # noqa E501
            )
        )
        ps().processResults(self.cmd, results)

        self.assertEqual(len(results.values), 3)

        cpu, cpuValue = _getDatapoint(results.values, "cpu")
        self.assertIsNotNone(cpu)
        self.assertEqual(cpuValue, 31)

        mem, memValue = _getDatapoint(results.values, "mem")
        self.assertIsNotNone(mem)
        self.assertEqual(memValue, 2 * 1024.0)

        count, countValue = _getDatapoint(results.values, "count")
        self.assertIsNotNone(count)
        self.assertEqual(countValue, 2)

        self.assertEqual(len(results.events), 2)
        self.assertTrue(
            all("Process up" in ev.get("summary", "") for ev in results.events)
        )


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestBasicPSParsing))
    suite.addTest(makeSuite(TestMultipleCollections))
    suite.addTest(makeSuite(TestEdgeCases))
    suite.addTest(makeSuite(TestDefunctProcesses))
    suite.addTest(makeSuite(TestCmdConfigs))

    return suite
