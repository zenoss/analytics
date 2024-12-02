##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import inspect
import types

from unittest import TestCase

from celery import states
from zope.component import getGlobalSiteManager

from ..interfaces import IJobStore
from ..manager import JobManager, JobRecord
from ..storage import JobStore
from .utils import subTest, RedisLayer


class JobManagerTest(TestCase):
    """Test the JobManager class."""

    layer = RedisLayer

    full = {
        "jobid": "123",
        "name": "zen.zenjobs.test.SomeJob",
        "summary": "Pause then exit",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/123.log",
        "created": 1551804881.024517,
        "started": 1551804891.863857,
        "finished": 1551805270.154359,
        "status": "SUCCESS",
    }

    def setUp(t):
        t.manager = JobManager("JobManagerTest")
        t.store = JobStore(t.layer.redis)
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis"
        )

    def tearDown(t):
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis"
        )
        del t.store
        del t.manager

    def test_api_existence(t):
        methods = (
            "addJobChain",
            "addJob",
            "wait",
            "query",
            "update",
            "getJob",
            "deleteJob",
            "getUnfinishedJobs",
            "getRunningJobs",
            "getPendingJobs",
            "getFinishedJobs",
            "getAllJobs",
            "clearJobs",
            "killRunning",
        )
        for name in methods:
            with subTest(method_name=name):
                method = getattr(JobManager, name, None)
                t.assertTrue(inspect.ismethod(method))
        all_methods = set(
            m
            for m in JobManager.__dict__
            if not m.startswith("_")
            and inspect.ismethod(getattr(JobManager, m, None))
        )
        missing = all_methods - set(methods)
        t.assertSetEqual(
            set({}),
            missing,
            "JobManager has some new methods since the last time this "
            "test was updated. Please update this test to include the "
            "new methods.",
        )

    def test_query_bad_criteria(t):
        with t.assertRaises(ValueError):
            t.manager.query(criteria={"blah": 1})

    def test_query_good_criteria(t):
        keys = {
            "status": "STARTED",
            "user": "joe",
            "userid": "joe",
        }
        for key, value in keys.items():
            criteria = {key: value}
            with subTest(criteria=criteria):
                t.manager.query(criteria=criteria)

    def test_good_sort_keys(t):
        t.store[t.full["jobid"]] = t.full
        keys = (
            "jobid",
            "name",
            "summary",
            "description",
            "userid",
            "logfile",
            "created",
            "started",
            "finished",
            "status",
            "uuid",
            "scheduled",
            "user",
        )
        for key in keys:
            with subTest(key=key):
                t.manager.query(key=key)

    def test_bad_sort_key(t):
        with t.assertRaises(ValueError):
            t.manager.query(key="details")

    def test_query_return_value(t):
        expected = {"jobs": (), "total": 0}
        actual = t.manager.query()
        t.assertDictEqual(expected, actual)

    def test_getUnfinishedJobs_all_types(t):
        expected = []
        # in celery 4.4.7 REJECTED was added to UNREADY_STATES (only used in events)
        # but it wasn't included to ALL_STATES
        for idx, st in enumerate(states.ALL_STATES | states.UNREADY_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            t.store[rec["jobid"]] = rec
            if st in states.UNREADY_STATES:
                expected.append(JobRecord.make(rec))
        actual = t.manager.getUnfinishedJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), len(states.UNREADY_STATES))
        t.assertItemsEqual(expected, actual)

    def test_getUnfinishedJobs_one_type(t):
        from Products.Jobber.jobs import PausingJob

        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            if st in states.UNREADY_STATES:
                if not expected:
                    rec["name"] = PausingJob.name
                    expected.append(JobRecord.make(rec))
            t.store[rec["jobid"]] = rec
        actual = t.manager.getUnfinishedJobs(PausingJob)
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 1)
        t.assertItemsEqual(expected, actual)

    def test_getUnfinishedJobs_wrong_state(t):
        t.store[t.full["jobid"]] = t.full
        actual = t.manager.getUnfinishedJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 0)

    def test_getUnfinishedJobs_with_bad_type(t):
        with t.assertRaises(ValueError):
            t.manager.getUnfinishedJobs("blah.blah")

    def test_getRunningJobs_all_types(t):
        running_states = (states.STARTED, states.RETRY)
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            t.store[rec["jobid"]] = rec
            if st in running_states:
                expected.append(JobRecord.make(rec))
        actual = t.manager.getRunningJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), len(running_states))
        t.assertItemsEqual(expected, actual)

    def test_getRunningJobs_one_type(t):
        from Products.Jobber.jobs import PausingJob

        running_states = (states.STARTED, states.RETRY)
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            if st in running_states:
                if not expected:
                    rec["name"] = PausingJob.name
                    expected.append(JobRecord.make(rec))
            t.store[rec["jobid"]] = rec
        actual = t.manager.getRunningJobs(PausingJob)
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 1)
        t.assertItemsEqual(expected, actual)

    def test_getRunningJobs_wrong_state(t):
        t.store[t.full["jobid"]] = t.full
        actual = t.manager.getRunningJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 0)

    def test_getRunningJobs_with_bad_type(t):
        with t.assertRaises(ValueError):
            t.manager.getRunningJobs("blah.blah")

    def test_getPendingJobs_all_types(t):
        pending_states = (states.RECEIVED, states.PENDING)
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            t.store[rec["jobid"]] = rec
            if st in pending_states:
                expected.append(JobRecord.make(rec))
        actual = t.manager.getPendingJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), len(pending_states))
        t.assertItemsEqual(expected, actual)

    def test_getPendingJobs_one_type(t):
        from Products.Jobber.jobs import PausingJob

        pending_states = (states.RECEIVED, states.PENDING)
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            if st in pending_states:
                if not expected:
                    rec["name"] = PausingJob.name
                    expected.append(JobRecord.make(rec))
            t.store[rec["jobid"]] = rec
        actual = t.manager.getPendingJobs(PausingJob)
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 1)
        t.assertItemsEqual(expected, actual)

    def test_getPendingJobs_wrong_state(t):
        t.store[t.full["jobid"]] = t.full
        actual = t.manager.getPendingJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 0)

    def test_getPendingJobs_with_bad_type(t):
        with t.assertRaises(ValueError):
            t.manager.getPendingJobs("blah.blah")

    def test_getFinishedJobs_all_types(t):
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            t.store[rec["jobid"]] = rec
            if st in states.READY_STATES:
                expected.append(JobRecord.make(rec))
        actual = t.manager.getFinishedJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), len(states.READY_STATES))
        t.assertItemsEqual(expected, actual)

    def test_getFinishedJobs_one_type(t):
        from Products.Jobber.jobs import PausingJob

        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            if st in states.READY_STATES:
                if not expected:
                    rec["name"] = PausingJob.name
                    expected.append(JobRecord.make(rec))
            t.store[rec["jobid"]] = rec
        actual = t.manager.getFinishedJobs(PausingJob)
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 1)
        t.assertItemsEqual(expected, actual)

    def test_getFinishedJobs_wrong_state(t):
        t.store[t.full["jobid"]] = dict(t.full, status=states.STARTED)
        actual = t.manager.getFinishedJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 0)

    def test_getFinishedJobs_with_bad_type(t):
        with t.assertRaises(ValueError):
            t.manager.getFinishedJobs("blah.blah")

    def test_getAllJobs_all_types(t):
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            t.store[rec["jobid"]] = rec
            expected.append(JobRecord.make(rec))
        actual = t.manager.getAllJobs()
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), len(states.ALL_STATES))
        t.assertItemsEqual(expected, actual)

    def test_getAllJobs_one_type(t):
        from Products.Jobber.jobs import PausingJob

        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            if not expected:
                rec["name"] = PausingJob.name
                expected.append(JobRecord.make(rec))
            t.store[rec["jobid"]] = rec
        actual = t.manager.getAllJobs(PausingJob)
        t.assertIsInstance(actual, types.GeneratorType)
        actual = list(actual)
        t.assertEqual(len(actual), 1)
        t.assertItemsEqual(expected, actual)

    def test_getAllJobs_with_bad_type(t):
        with t.assertRaises(ValueError):
            t.manager.getFinishedJobs("blah.blah")

    def test_clearJobs(t):
        expected = []
        for idx, st in enumerate(states.ALL_STATES):
            rec = dict(t.full, status=st, jobid="abc-{}".format(idx))
            t.store[rec["jobid"]] = rec
            if st not in states.READY_STATES:
                expected.append(JobRecord.make(rec))
        t.manager.clearJobs()
        actual = [JobRecord.make(val) for val in t.store.values()]
        t.assertItemsEqual(expected, actual)
