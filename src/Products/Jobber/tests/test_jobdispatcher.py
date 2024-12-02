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

from celery.canvas import Signature, chain
from mock import call, Mock, patch
from transaction.interfaces import IDataManager
from zope.interface.verify import verifyClass, verifyObject

from ..manager import JobDispatcher
from ..storage import JobStore


class JobDispatcherTest(TestCase):
    """Test the JobDispatcher class."""

    def setUp(t):
        t.storage = Mock(spec=JobStore)
        t.dispatcher = JobDispatcher(t.storage)

    def tearDown(t):
        del t.storage
        del t.dispatcher

    def test_implements_interface(t):
        t.assertTrue(verifyClass(IDataManager, JobDispatcher))
        t.assertTrue(verifyObject(IDataManager, t.dispatcher))

    def test_initial_state(t):
        t.assertTupleEqual((), t.dispatcher.staged)

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_add(t, _transaction, _stage_record):
        sig = Signature("mock.task", args=(10,), options={"task_id": "1"})
        t.dispatcher.add(sig)
        t.assertTupleEqual((sig.id,), t.dispatcher.staged)
        tx = _transaction.get.return_value
        tx.join.assert_called_once_with(t.dispatcher)
        _stage_record.assert_called_once_with(t.storage, sig)

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_add_chain(t, _transaction, _stage_record):
        sig1 = Signature("mock.task", args=(4,), options={"task_id": "1"})
        sig2 = Signature("mock.task", args=(5,), options={"task_id": "2"})
        sig = chain(sig1, sig2)
        t.dispatcher.add(sig)
        expected = (sig1.id, sig2.id)
        t.assertTupleEqual(expected, t.dispatcher.staged)
        tx = _transaction.get.return_value
        tx.join.assert_called_once_with(t.dispatcher)
        calls = [call(t.storage, sig1), call(t.storage, sig2)]
        _stage_record.assert_has_calls(calls)

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_discard(t, _transaction, _stage_record):
        sig = Signature("mock.task", args=(10,), options={"task_id": "1"})
        t.dispatcher.add(sig)
        t.dispatcher.discard("1")
        t.assertTupleEqual((), t.dispatcher.staged)
        t.storage.mdelete.assert_called_once_with("1")

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_abort(t, _transaction, _stage_record):
        sig = Signature("mock.task", args=(10,), options={"task_id": "1"})
        tx = Mock()
        t.dispatcher.add(sig)
        t.dispatcher.abort(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.storage.mdelete.assert_called_once_with("1")
        t.assertListEqual([], t.dispatcher._signatures)

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_tpc_abort(t, _transaction, _stage_record):
        sig = Signature("mock.task", args=(10,), options={"task_id": "1"})
        tx = Mock()
        t.dispatcher.add(sig)
        t.dispatcher.abort(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.storage.mdelete.assert_called_once_with("1")
        t.assertListEqual([], t.dispatcher._signatures)

    @patch("Products.Jobber.manager.commit_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_tpc_finish(t, _transaction, _stage, _commit):
        sig = Signature("mock.task", args=(10,), options={"task_id": "1"})
        apply_mock = Mock()
        sig.apply_async = apply_mock
        tx = Mock()
        t.dispatcher.add(sig)
        t.dispatcher.tpc_finish(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.assertListEqual([], t.dispatcher._signatures)
        t.storage.mdelete.assert_not_called()
        apply_mock.assert_called_once_with()
        _commit.assert_called_once_with(t.storage, sig)

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_abort_chain(t, _transaction, _stage_record):
        sig1 = Signature("mock.task", args=(4,), options={"task_id": "1"})
        sig2 = Signature("mock.task", args=(5,), options={"task_id": "2"})
        sig = chain(sig1, sig2)
        tx = Mock()
        t.dispatcher.add(sig)
        t.dispatcher.abort(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.storage.mdelete.assert_called_once_with("1", "2")
        t.assertListEqual([], t.dispatcher._signatures)

    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_tpc_abort_chain(t, _transaction, _stage_record):
        sig1 = Signature("mock.task", args=(4,), options={"task_id": "1"})
        sig2 = Signature("mock.task", args=(5,), options={"task_id": "2"})
        sig = chain(sig1, sig2)
        tx = Mock()
        t.dispatcher.add(sig)
        t.dispatcher.abort(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.storage.mdelete.assert_called_once_with("1", "2")
        t.assertListEqual([], t.dispatcher._signatures)

    @patch("Products.Jobber.manager.commit_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_tpc_finish_chain(t, _transaction, _stage, _commit):
        sig1 = Signature("mock.task", args=(4,), options={"task_id": "1"})
        sig2 = Signature("mock.task", args=(5,), options={"task_id": "2"})
        sig = chain(sig1, sig2)
        apply_mock = Mock()
        sig.apply_async = apply_mock
        tx = Mock()
        t.dispatcher.add(sig)
        t.dispatcher.tpc_finish(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.assertListEqual([], t.dispatcher._signatures)
        t.storage.mdelete.assert_not_called()
        apply_mock.assert_called_once_with()
        calls = [call(t.storage, sig1), call(t.storage, sig2)]
        _commit.assert_has_calls(calls)

    @patch("Products.Jobber.manager.commit_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.stage_jobrecord", autospec=True)
    @patch("Products.Jobber.manager.transaction", autospec=True)
    def test_tpc_finish_multiple(t, _transaction, _stage, _commit):
        sig1 = Signature("mock.task", args=(10,), options={"task_id": "1"})
        sig2 = Signature("mock.task", args=(11,), options={"task_id": "2"})
        apply1 = Mock()
        sig1.apply_async = apply1
        apply2 = Mock()
        sig2.apply_async = apply2
        tx = Mock()

        t.dispatcher.add(sig1)
        t.dispatcher.add(sig2)

        t.dispatcher.tpc_finish(tx)
        t.assertTupleEqual((), t.dispatcher.staged)
        t.assertListEqual([], t.dispatcher._signatures)
        t.storage.mdelete.assert_not_called()
        apply1.assert_called_once_with()
        apply2.assert_called_once_with()
        calls = [call(t.storage, sig1), call(t.storage, sig2)]
        _commit.assert_has_calls(calls)
