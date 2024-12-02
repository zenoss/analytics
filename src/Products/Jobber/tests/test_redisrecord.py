##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from ..jobs import Job
from ..model import RedisRecord
from ..zenjobs import app


class BaseBuildRedisRecord(object):
    def setUp(t):
        t.args = (10,)
        t.kw = {"named": "charger"}
        t.jobid = "12345"
        t.expected = {
            "logfile": "/opt/zenoss/log/jobs/%s.log" % t.jobid,
            "description": t.task.description_from(*t.args, **t.kw),
            "summary": t.task.summary,
            "name": t.task.name,
            "jobid": t.jobid,
        }

    def tearDown(t):
        del t.task
        del t.args
        del t.kw
        del t.jobid
        del t.expected

    def test_bad_jobid(t):
        with t.assertRaises(ValueError):
            RedisRecord.from_task(t.task, None, (), {})

    def test_minimum_args(t):
        actual = RedisRecord.from_task(t.task, t.jobid, t.args, t.kw)
        t.assertDictEqual(t.expected, actual)

    def test_non_default_description(t):
        description = "alternate description"
        t.expected["description"] = description
        actual = RedisRecord.from_task(
            t.task, t.jobid, t.args, t.kw, description=description
        )
        t.assertDictEqual(t.expected, actual)

    def test_status(t):
        status = "PENDING"
        t.expected["status"] = status
        actual = RedisRecord.from_task(
            t.task, t.jobid, t.args, t.kw, status=status
        )
        t.assertDictEqual(t.expected, actual)

    def test_created(t):
        created = 1234970434.303
        t.expected["created"] = created
        actual = RedisRecord.from_task(
            t.task, t.jobid, t.args, t.kw, created=created
        )
        t.assertDictEqual(t.expected, actual)

    def test_userid(t):
        userid = "someuser"
        t.expected["userid"] = userid
        actual = RedisRecord.from_task(
            t.task, t.jobid, t.args, t.kw, userid=userid
        )
        t.assertDictEqual(t.expected, actual)

    def test_details(t):
        details = {"a": 1, "b": 2}
        t.expected["details"] = details
        actual = RedisRecord.from_task(
            t.task, t.jobid, t.args, t.kw, details=details
        )
        t.assertDictEqual(t.expected, actual)

    def test_all_defaulted_args(t):
        status = "PENDING"
        created = 1234970434.303
        userid = "someuser"
        details = {"a": 1, "b": 2}
        t.expected.update(
            {
                "status": status,
                "created": created,
                "userid": userid,
                "details": details,
            }
        )
        actual = RedisRecord.from_task(
            t.task,
            t.jobid,
            t.args,
            t.kw,
            status=status,
            created=created,
            userid=userid,
            details=details,
        )
        t.assertDictEqual(t.expected, actual)

    def test_from_signature(t):
        sig = t.task.s(*t.args, **t.kw).set(task_id=t.jobid)
        actual = RedisRecord.from_signature(sig)
        t.assertDictEqual(t.expected, actual)

    def test_from_signature_with_userid(t):
        userid = "blink"
        t.expected["userid"] = userid
        sig = t.task.s(*t.args, **t.kw).set(task_id=t.jobid)
        sig.options.setdefault("headers", {})["userid"] = userid
        actual = RedisRecord.from_signature(sig)
        t.assertDictEqual(t.expected, actual)

    def test_from_signature_with_details(t):
        details = {"a": 1, "b": 2}
        t.expected["details"] = details
        sig = t.task.s(*t.args, **t.kw).set(task_id=t.jobid).set(**details)
        actual = RedisRecord.from_signature(sig)
        t.assertDictEqual(t.expected, actual)

    def test_from_signature_with_custom_description(t):
        desc = "another description"
        t.expected["description"] = desc
        sig = t.task.s(*t.args, **t.kw).set(task_id=t.jobid)
        sig = sig.set(description=desc)
        actual = RedisRecord.from_signature(sig)
        t.assertDictEqual(t.expected, actual)

    def test_from_signal(t):
        userid = "blink"
        t.expected["userid"] = userid
        body = (t.args, t.kw, {})
        headers = {"userid": userid, "task": t.task.name, "id": t.jobid}
        properties = {}
        actual = RedisRecord.from_signal(body, headers, properties)
        t.assertDictEqual(t.expected, actual)

    def test_from_signal_with_details(t):
        body = (t.args, t.kw, {})
        headers = {"id": t.jobid, "task": t.task.name}
        properties = {"a": 1, "b": 2}
        t.expected["details"] = properties
        actual = RedisRecord.from_signal(body, headers, properties)
        t.assertDictEqual(t.expected, actual)


class BuildRedisRecordFromJobTest(BaseBuildRedisRecord, TestCase):
    """Test the RedisRecord class with a Job."""

    class TestJob(Job):
        name = "TestJob"
        @classmethod
        def getJobType(cls):
            return "Test Job"

        @classmethod
        def getJobDescription(cls, *args, **kw):
            return "TestJob %s %s" % (args, kw)

    from Products.Jobber.zenjobs import app
    app.register_task(TestJob)

    def setUp(t):
        t.task = t.TestJob()
        BaseBuildRedisRecord.setUp(t)


class BuildRedisRecordFromZenTaskTest(BaseBuildRedisRecord, TestCase):
    """Test the RedisRecord class with a ZenTask."""

    @app.task(
        bind=True,
        name="zen.zenjobs.test.test_task",
        summary="Test ZenTask",
        description_template="Test {0} named={named}",
    )
    def noop_task(self, *args, **kw):
        pass

    def setUp(t):
        t.task = t.noop_task
        BaseBuildRedisRecord.setUp(t)
