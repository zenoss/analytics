##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import types

from unittest import TestCase

from celery import states
from mock import patch, Mock
from zope.component import getGlobalSiteManager

from ..model import (
    IJobStore,
    job_start,
    job_end,
    job_success,
    job_failure,
    job_retry,
)
from ..storage import JobStore
from .utils import subTest, RedisLayer
from ..zenjobs import app

UNEXPECTED = type("UNEXPECTED", (object,), {})()
PATH = {"src": "Products.Jobber.model"}


class _CommonFixture(object):

    jobid = "123"

    initial = {
        "jobid": jobid,
        "name": "TestJob",
        "summary": "Products.Jobber.jobs.TestJob",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/%s.log" % jobid,
        "created": 1551804881.024517,
        "status": "PENDING",
    }

    def setUp(t):
        t.store = JobStore(t.layer.redis)
        t.store[t.jobid] = t.initial
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis"
        )
        rootLogger = logging.getLogger()
        t.handlers = rootLogger.handlers
        rootLogger.handlers = []

    def tearDown(t):
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis"
        )
        del t.store
        rootLogger = logging.getLogger()
        rootLogger.handlers = t.handlers
        del t.handlers


class JobStartTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_already_finished(t, _time):
        for status in states.READY_STATES:
            t.store.update(t.jobid, status=status)
            with subTest(status=status):
                job_start(t.jobid)
                t.assertEqual(t.store.getfield(t.jobid, "status"), status)
                _time.time.assert_not_called()

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_started(t, _time):
        tm = 1597059131.762538
        _time.time.return_value = tm

        expected_status = states.STARTED
        expected_started = tm
        expected_finished = None

        job_start(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    def test_already_aborted(t):
        expected_started = None
        expected_status = states.ABORTED
        t.store.update(t.jobid, status=expected_status)

        job_start(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)


class JobSuccessTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("Products.Jobber.zenjobs.app.backend", autospec=True)
    def test_success(t, _backend, _time):
        tm = 1597059131.762538

        req = type("request", (object,), {"id": t.jobid})()
        sender = type(
            "sender",
            (object,),
            {"request": req, "ignore_result": False},
        )()

        expected_status = states.SUCCESS
        expected_started = tm - 10
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        t.store.update(t.jobid, started=expected_started)

        job_success(None, sender=sender)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)


class JobFailureTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        job_start("1")

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("Products.Jobber.zenjobs.app.backend", autospec=True)
    def test_aborted(t, _backend, _time):
        tm = 1597059131.762538

        expected_status = states.ABORTED
        expected_started = None
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        job_failure(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("Products.Jobber.zenjobs.app.backend", autospec=True)
    def test_failure(t, _backend, _time):
        tm = 1597059131.762538

        expected_status = states.FAILURE
        expected_started = None
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        job_failure(t.jobid)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("Products.Jobber.zenjobs.app.backend", autospec=True)
    def test_callbacks_are_aborted(t, _backend, _time):
        next_jobid = "456"
        next_job = dict(t.initial)
        next_job["jobid"] = next_jobid
        t.store[next_jobid] = next_job

        request = type(
            "request",
            (object,),
            {"callbacks": [{"options": {"task_id": next_jobid}}]},
        )()
        sender = type(
            "task",
            (object,),
            {"request": request, "ignore_result": False},
        )()

        tm = 1597059131.762538

        expected_status = states.ABORTED
        expected_started = None
        expected_finished = tm

        _backend.get_status.return_value = expected_status
        _time.time.return_value = expected_finished

        job_failure(t.jobid, sender=sender)

        for jobid in (t.jobid, next_jobid):
            with subTest(jobid=jobid):
                status = t.store.getfield(jobid, "status")
                started = t.store.getfield(jobid, "started")
                finished = t.store.getfield(jobid, "finished")

                t.assertEqual(expected_status, status)
                t.assertEqual(expected_started, started)
                t.assertEqual(expected_finished, finished)


class JobRetryTest(_CommonFixture, TestCase):

    layer = RedisLayer

    def test_unknown_task_id(t):
        req = type("request", (object,), {"id": "1"})()
        job_retry(req)

    @patch("Products.Jobber.zenjobs.app.backend", autospec=True)
    def test_nominal(t, _backend):
        tm = 1597059131.762538
        req = type("request", (object,), {"id": t.jobid})()

        expected_status = states.RETRY
        expected_started = tm
        expected_finished = None

        _backend.get_status.return_value = expected_status

        t.store.update(t.jobid, started=expected_started)
        job_retry(req)

        status = t.store.getfield(t.jobid, "status")
        started = t.store.getfield(t.jobid, "started")
        finished = t.store.getfield(t.jobid, "finished")

        t.assertEqual(expected_status, status)
        t.assertEqual(expected_started, started)
        t.assertEqual(expected_finished, finished)


@app.task(
    bind=True,
    name="zen.zenjobs.test.result_ignored_task",
    summary="Result Ignored Task",
    ignore_result=True,
)
def noop_task(self, *args, **kw):
    pass


class IgnoreResultTest(TestCase):
    """Test update_job_status when a task's ignore_result is True."""

    @patch("{src}.getUtility".format(**PATH))
    def test_job_start(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_start(task_id="0", task=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_success(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_success(None, sender=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_failure(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_failure(task_id="0", sender=task)
        _getUtility.assert_not_called()

    @patch("{src}.getUtility".format(**PATH))
    def test_job_retry(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        job_retry(None, sender=task)
        _getUtility.assert_not_called()


# Super fragile code here!!!!
# Unwrapping a decorated function!
# This only works as expected if job_end is declared as follows:
#
#    @inject_logger(log=mlog)
#    @_catch_exception
#    def job_end(log, task_id, task=None, **ignored):
#        ....
#
job_end = next(
    (
        c.cell_contents
        for c in job_end.func_closure
        if isinstance(c.cell_contents, types.FunctionType)
    ),
    None,
)


class JobEndTest(TestCase):
    """Test job_end task_postrun signal handler."""

    layer = RedisLayer

    def setUp(t):
        t.store = JobStore(t.layer.redis)
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis"
        )

    def tearDown(t):
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis"
        )
        del t.store

    @patch("{src}.getUtility".format(**PATH))
    def test_ignore_result_task(t, _getUtility):
        task = app.tasks.get("zen.zenjobs.test.result_ignored_task")
        log = Mock()
        job_end(log, "123", task=task)
        log.debug.assert_not_called()
        log.info.assert_not_called()
        _getUtility.assert_not_called()

    def test_unknown_taskid(t):
        log = Mock()
        job_end(log, "123")
        log.debug.assert_called_once_with("job not found")
        log.info.assert_not_called()

    def test_job_not_started(t):
        t.store["123"] = {
            "jobid": "123",
        }
        log = Mock()
        job_end(log, "123")
        log.debug.assert_called_once_with("job never started")
        log.info.assert_not_called()

    def test_job_not_done(t):
        for n, status in enumerate(states.UNREADY_STATES):
            taskid = str(123 + n)
            t.store[taskid] = {
                "jobid": taskid,
                "started": 1605015326.914606,
                "status": status,
            }
            log = Mock()
            expected = ("job not done  status=%s", status)
            with subTest(taskid=taskid, status=status):
                job_end(log, taskid)
                log.debug.assert_called_once_with(*expected)
                log.info.assert_not_called()

    def test_job_finished(t):
        started = 1605015326.914606
        finished = 1605015336.914606
        expected = ("Job total duration is %0.3f seconds", finished - started)
        for n, status in enumerate(states.READY_STATES):
            taskid = str(123 + n)
            t.store[taskid] = {
                "jobid": taskid,
                "started": started,
                "finished": finished,
                "status": status,
            }
            log = Mock()
            with subTest(taskid=taskid, status=status):
                job_end(log, taskid)
                log.debug.assert_not_called()
                log.info.assert_called_once_with(*expected)
