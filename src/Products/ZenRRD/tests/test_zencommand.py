##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.

# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase

from mock import patch
from twisted.internet import reactor
from twisted.python.failure import Failure

from Products.ZenRRD.zencommand import (
    defer,
    SshPerformanceCollectionTask,
    TimeoutError,
)

PATH = {"src": "Products.ZenRRD.zencommand"}


class TestSshPerformanceCollectionTask(TestCase):
    def setUp(t):
        # Patch out the queryUtility, don't need it.
        t.queryUtility_patcher = patch(
            "{src}.queryUtility".format(**PATH),
            autospec=True,
        )
        t.queryUtility_patcher.start()
        t.addCleanup(t.queryUtility_patcher.stop)

        t.makeExecutor_patcher = patch(
            "{src}.makeExecutor".format(**PATH),
            autospec=True,
        )
        t._executor = t.makeExecutor_patcher.start()
        t.addCleanup(t.makeExecutor_patcher.stop)

        t._task = SshPerformanceCollectionTask(
            "test_device",
            "test_config_id",
            300,
            type(
                "Config",
                (object,),
                {
                    "id": "test_device",
                    "manageIp": "1.2.3.4",
                    "zSshConcurrentSessions": 2,
                    "datasources": [],
                    "zCommandCommandTimeout": 60,
                },
            )(),
        )
        t._task._commandMap = {
            "command": ["datasource"],
        }

    def test_fetchPerf_success(t):
        submit_d = defer.Deferred()
        executor = _Executor(submit_d)
        t._task._executor = executor

        response = type(
            "Response",
            (object,),
            {
                "exitCode": 2,
                "stdout": "win",
                "stderr": "",
            },
        )()
        submit_d.callback(response)

        def result(*args):
            expected = (((True, ("command", response)),),)
            t.assertTupleEqual(expected, args)

        fetch_d = t._task._fetchPerf()
        fetch_d.addBoth(result)

        reactor.runUntilCurrent()

    def test_fetchPerf_error(t):
        submit_d = defer.Deferred()
        executor = _Executor(submit_d)
        t._task._executor = executor
        failure = Failure(TimeoutError("done"))
        submit_d.errback(failure)

        def result(*args):
            expected = (((False, ("command", failure)),),)
            t.assertTupleEqual(expected, args)

        fetch_d = t._task._fetchPerf()
        fetch_d.addBoth(result)

        reactor.runUntilCurrent()


class _Executor(object):
    def __init__(self, rv):
        self._rv = rv

    def submit(self, *args, **kw):
        return self._rv
