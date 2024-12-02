##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from celery import Task
from celery.canvas import Signature
from mock import patch
from unittest import TestCase

from ..task.base import _default_summary, ZenTask
from ..zenjobs import app


class ZenTaskTest(TestCase):
    """Test the ZenTask class."""

    task_template = "Test {0} named={named}"
    task_summary = "Test ZenTask"
    task_name = "zen.zenjobs.test.test_task"

    @app.task(
        bind=True,
        name=task_name,
        summary=task_summary,
        description_template=task_template,
    )
    def simple_task(self, *args, **kw):
        pass

    @app.task(
        bind=True,
        name="default_summary",
    )
    def defaults_task(self, *args, **kw):
        pass

    def test_default_task_class(t):
        t.assertEqual("Products.Jobber.task:ZenTask", app.task_cls)

    def test_type(t):
        t.assertIsInstance(t.simple_task, ZenTask)
        t.assertIsInstance(t.simple_task, Task)

    def test_description_template(t):
        t.assertEqual(t.task_template, t.simple_task.description_template)

    def test_summary(t):
        t.assertEqual(t.task_summary, t.simple_task.summary)

    def test_name(t):
        t.assertEqual(t.task_name, t.simple_task.name)

    def test_default_summary(t):
        expected = _default_summary.format(t.defaults_task)
        t.assertEqual(expected, t.defaults_task.summary)

    def test_default_description(t):
        expected = _default_summary.format(t.defaults_task)
        t.assertEqual(expected, t.defaults_task.description)

    def test_description_from(t):
        args = (10,)
        kw = {"named": "blah"}
        expected = t.task_template.format(*args, **kw)
        actual = t.simple_task.description_from(*args, **kw)
        t.assertEqual(expected, actual)

    def test_description_from_no_template(t):
        args = (10,)
        kw = {"named": "blah"}
        expected = t.defaults_task.summary
        actual = t.defaults_task.description_from(*args, **kw)
        t.assertEqual(expected, actual)

    def test_description_from_missing_args(t):
        kw = {"named": "blah"}
        with t.assertRaises(IndexError):
            t.simple_task.description_from(**kw)

    def test_description_from_missing_kwargs(t):
        args = (10,)
        with t.assertRaises(KeyError):
            t.simple_task.description_from(*args)

    @patch("Products.Jobber.task.base.get_task_logger", autospec=True)
    def test_log(t, _get_task_logger):
        log = t.simple_task.log
        _get_task_logger.assert_called_with(t.task_name)
        t.assertEqual(_get_task_logger.return_value, log)

    @patch("Products.Jobber.task.base.uuid", autospect=True)
    def test_subtask(t, _uuid):
        task_id = "123"
        _uuid.uuid4.return_value = task_id
        expected = {
            "headers": {"userid": None},
            "task_id": task_id,
        }
        task = t.simple_task.signature()
        t.assertIsInstance(task, Signature)
        t.assertDictEqual(expected, task.options)
