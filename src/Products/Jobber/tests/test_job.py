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

from unittest import TestCase

from celery.contrib.abortable import AbortableTask

from ..exceptions import NoSuchJobException
from ..jobs import Job
from ..task import ZenTask
from ..zenjobs import app
from .utils import subTest


class JobAPITest(TestCase):
    """Test the Job class."""

    def test_job_api(t):
        methods = (
            "getJobType",
            "getJobDescription",
            "makeSubJob",
            "setProperties",
            "_run",
        )
        for name in methods:
            with subTest(method_name=name):
                method = getattr(Job, name, None)
                t.assertTrue(inspect.ismethod(method))

        not_methods = ("log", "dmd")
        for name in not_methods:
            with subTest(attr_name=name):
                attr = getattr(Job, name, None)
                t.assertFalse(inspect.ismethod(attr))

    def test_is_abstract(t):
        t.assertTrue(
            not any(name.split(".")[-1] == "Job" for name in app.tasks.keys())
        )

    def test_job_is_task(t):
        t.assertTrue(issubclass(Job, ZenTask))

    def test_job_is_abortable(t):
        t.assertTrue(issubclass(Job, AbortableTask))

    def test_undefined_job_type(t):
        t.assertEqual(Job.getJobType(), None)

    def test_unimplemented_job_description(t):
        with t.assertRaises(NotImplementedError):
            Job.getJobDescription()
        with t.assertRaises(NotImplementedError):
            Job.description_from()

    def test_makeSubJob_fails(t):
        with t.assertRaises(NoSuchJobException):
            Job.makeSubJob()
