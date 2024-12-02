##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import itertools
import types

from unittest import TestCase

from mock import patch

from Products.Zuul import marshal
from Products.Zuul.interfaces import IMarshallable, IInfo

from ..model import (
    IJobRecord,
    JobRecord,
    JobRecordMarshaller,
    LegacySupport,
)
from ..storage import Fields
from .utils import subTest

UNEXPECTED = type("UNEXPECTED", (object,), {})()
PATH = {"src": "Products.Jobber.model"}


class JobRecordTest(TestCase):
    """Test the JobRecord class."""

    def setUp(t):
        t.data = {
            "jobid": "123",
            "name": "Products.Jobber.jobs.FooJob",
            "summary": "FooJob",
            "description": "A foo job",
            "userid": "zenoss",
            "logfile": "/opt/zenoss/log/jobs/123.log",
            "created": 1551804881.024517,
            "started": 1551804891.863857,
            "finished": 1551805270.154359,
            "status": "SUCCESS",
            "details": {
                "foo": "foo string",
                "bar": 123,
                "baz": 34597945.00234,
            },
        }

    def test_interfaces(t):
        for intf in (IJobRecord, IMarshallable, IInfo):
            with subTest(interface=intf):
                t.assertTrue(intf.implementedBy(JobRecord))
                j = JobRecord.make({})
                t.assertTrue(intf.providedBy(j))

    def test_attributes(t):
        # Assert that JobRecord has all the attributes specified by Fields.
        j = JobRecord.make({})
        missing_names = set(Fields.viewkeys()) - set(dir(j))
        t.assertSetEqual(set(), missing_names)

    def test_has_methods(t):
        # Assert that the appropriate methods exist.
        methods = ("abort", "wait")
        for m in methods:
            with subTest(method=m):
                result = getattr(JobRecord, m, None)
                t.assertIsInstance(result, types.UnboundMethodType)

    def test_dir_keys(t):
        j = JobRecord.make(t.data)
        expected = t.data.keys()
        expected.remove("details")
        expected.extend(t.data["details"].keys())
        expected.extend(
            (
                "details",
                "id",
                "make",
                "uid",
                "uuid",
                "duration",
                "complete",
                "abort",
                "wait",
                "result",
                "job_description",
                "job_name",
                "job_type",
            )
        )
        expected = sorted(expected)
        actual = [a for a in dir(j) if not a.startswith("__")]
        t.assertListEqual(expected, actual)

    def test_job_description(t):
        j = JobRecord.make(t.data)
        t.assertEqual(j.job_description, j.description)

    def test_job_name(t):
        j = JobRecord.make(t.data)
        t.assertEqual(j.job_name, j.name)

    def test_job_type(t):
        from Products.Jobber.jobs import FacadeMethodJob

        data = dict(t.data)
        data["name"] = FacadeMethodJob.name
        j = JobRecord.make(data)
        t.assertEqual(j.job_type, FacadeMethodJob.getJobType())

    def test_details_are_exposed(t):
        j = JobRecord.make({})
        j.details = {"foo": 1}
        t.assertEqual(1, j.foo)
        t.assertIn("foo", dir(j))
        t.assertIn("foo", j.__dict__)
        t.assertEqual(1, j.__dict__["foo"])

    def test_details_are_not_writable(t):
        j = JobRecord.make({})
        j.details = {"foo": 1}
        with t.assertRaises(AttributeError):
            j.foo = 3

    def test_make_badfield(t):
        with t.assertRaises(AttributeError):
            JobRecord.make({"foo": 1})

    def test_uuid(t):
        job = JobRecord.make(t.data)
        t.assertEqual(job.jobid, job.uuid)

    def test_make(t):
        actual = JobRecord.make(t.data)
        expected = itertools.chain(
            t.data.items(),
            (
                ("complete", True),
                ("duration", t.data["finished"] - t.data["started"]),
            ),
        )
        for attribute, expected_value in expected:
            actual_value = getattr(actual, attribute, UNEXPECTED)
            with subTest(attribute=attribute):
                t.assertEqual(expected_value, actual_value)

    def test_complete(t):
        parameters = {
            ("PENDING", False),
            ("RETRY", False),
            ("RECEIVED", False),
            ("STARTED", False),
            ("REVOKED", True),
            ("ABORTED", True),
            ("FAILURE", True),
            ("SUCCESS", True),
        }
        record = JobRecord.make(t.data)
        for status, expected in parameters:
            with subTest(status=status):
                record.status = status
                t.assertEqual(
                    expected, record.complete, msg="status=%s" % status
                )

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_duration(t, time):
        current_tm = 1551804885.298103
        completed_duration = t.data["finished"] - t.data["started"]
        incomplete_duration = current_tm - t.data["started"]
        time.time.return_value = current_tm
        parameters = {
            ("PENDING", None),
            ("RETRY", incomplete_duration),
            ("RECEIVED", None),
            ("STARTED", incomplete_duration),
            ("REVOKED", completed_duration),
            ("ABORTED", completed_duration),
            ("FAILURE", completed_duration),
            ("SUCCESS", completed_duration),
        }
        record = JobRecord.make(t.data)
        for status, expected in parameters:
            with subTest(status=status):
                record.status = status
                t.assertEqual(expected, record.duration)


class ComponentsLoadedLayer(object):
    includes = """
    <configure xmlns="http://namespaces.zope.org/zope">
        <include package="zope.component" file="meta.zcml"/>
        <include package="zope.security" file="meta.zcml"/>
        <include package="zope.browserpage" file="meta.zcml"/>
    </configure>
    """

    @classmethod
    def setUp(cls):
        import os.path
        from OFS.Application import import_products
        from zope.configuration import xmlconfig
        import Products.Jobber

        import_products()
        cls._ctx = xmlconfig.string(cls.includes)
        cls._ctx = xmlconfig.file(
            os.path.join(
                os.path.dirname(Products.Jobber.__file__), "configure.zcml"
            ),
            Products.Jobber,
            cls._ctx,
        )

    @classmethod
    def tearDown(cls):
        from zope.testing import cleanup

        cleanup.cleanUp()
        del cls._ctx


class JobRecordMarshallerTest(TestCase):
    """Test the JobRecordMarshaller class."""

    layer = ComponentsLoadedLayer

    def setUp(t):
        t.jobid = "12345"
        t.fields = {
            "description": "A test job record",
            "summary": "A Test",
            "name": "test",
            "jobid": t.jobid,
        }
        t.allfields = dict(
            t.fields,
            **{
                "status": None,
                "created": None,
                "finished": None,
                "started": None,
                "userid": None,
                "uuid": t.jobid,
            }
        )
        t.record = JobRecord.make(t.fields)

    def test_default_marshal(t):
        expected = {
            k: t.allfields[k]
            for k in JobRecordMarshaller._default_keys
            if k in t.allfields
        }
        serialized = marshal(t.record)
        t.assertDictEqual(expected, serialized)

    def test_keyed_marshal(t):
        keys = ("uuid", "name", "description")
        expected = {
            "uuid": t.allfields["jobid"],
            "name": t.allfields["name"],
            "description": t.allfields["description"],
        }
        serialized = marshal(t.record, keys=keys)
        t.assertDictEqual(expected, serialized)


class LegacySupportTest(TestCase):
    """Test the LegacySupport class."""

    def test_new_keys(t):
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
        )
        for key in keys:
            with subTest(key=key):
                actual = LegacySupport.from_key(key)
                t.assertEqual(key, actual)

    def test_legacy_keys(t):
        keys = {
            "uuid": "jobid",
            "scheduled": "created",
            "user": "userid",
        }
        for key in keys:
            with subTest(key=key):
                actual = LegacySupport.from_key(key)
                t.assertEqual(keys[key], actual)
