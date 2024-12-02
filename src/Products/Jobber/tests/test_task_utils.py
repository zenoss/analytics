##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from mock import MagicMock, mock_open, patch
from zope.component import getGlobalSiteManager, ComponentLookupError

from Products.Jobber.task.utils import job_log_has_errors

from ..interfaces import IJobStore
from ..storage import JobStore
from .utils import RedisLayer

PATH = {"src": "Products.Jobber.task.utils"}


class JobLogHasErrorsTest(TestCase):
    """Test the task.utils.job_log_has_errors function."""

    layer = RedisLayer

    record = {
        "jobid": "123",
        "name": "TestJob",
        "summary": "Products.Jobber.jobs.TestJob",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/123.log",
        "created": 1551804881.024517,
        "status": "PENDING",
    }

    def setUp(t):
        t.store = JobStore(t.layer.redis)
        t.store[t.record["jobid"]] = t.record
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis"
        )

    def tearDown(t):
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis"
        )
        del t.store

    def test_missing_jobstore(t):
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis"
        )
        with t.assertRaises(ComponentLookupError):
            job_log_has_errors("123")

    def test_undefined_logfile_name(t):
        t.store.update("123", logfile=None)
        t.assertFalse(job_log_has_errors("123"))

    def test_blank_logfile_name(t):
        t.store.update("123", logfile="")
        t.assertFalse(job_log_has_errors("123"))

    def test_bad_logfile(t):
        m = MagicMock(side_effect=RuntimeError("boom"))
        _open = mock_open(m)
        with patch("__builtin__.open", _open):
            t.assertFalse(job_log_has_errors("123"))

    def test_no_errors(t):
        _open = mock_open(
            read_data=(
                "INFO zen.zenjobs good things\n"
                "WARNING zen.zenjobs be alert\n"
                "DEBUG zen.zenjobs noisy things\n"
            )
        )
        with patch("__builtin__.open", _open):
            t.assertFalse(job_log_has_errors("123"))

    def test_has_errors(t):
        _open = mock_open(
            read_data=(
                "INFO zen.zenjobs good things\n"
                "ERROR zen.zenjobs bad things\n"
                "DEBUG zen.zenjobs noisy things\n"
            )
        )
        with patch("__builtin__.open", _open):
            t.assertTrue(job_log_has_errors("123"))
