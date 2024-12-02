from mock import Mock
from unittest import TestCase

from ..errors import (
    ConflictError,
    pb,
    RemoteException,
    RemoteBadMonitor,
    RemoteConflictError,
    translateError,
)


class RemoteExceptionsTest(TestCase):
    """These exceptions can probably be moved into their own module"""

    def test_raise_RemoteException(t):
        with t.assertRaises(RemoteException):
            raise RemoteException("message", "traceback")

    def test_RemoteException_is_pb_is_copyable(t):
        t.assertTrue(issubclass(RemoteException, pb.Copyable))
        t.assertTrue(issubclass(RemoteException, pb.RemoteCopy))

    def test_raise_RemoteConflictError(t):
        with t.assertRaises(RemoteConflictError):
            raise RemoteConflictError("message", "traceback")

    def test_RemoteConflictError_is_pb_is_copyable(t):
        t.assertTrue(issubclass(RemoteConflictError, pb.Copyable))
        t.assertTrue(issubclass(RemoteConflictError, pb.RemoteCopy))

    def test_raise_RemoteBadMonitor(t):
        with t.assertRaises(RemoteBadMonitor):
            raise RemoteBadMonitor("message", "traceback")

    def test_RemoteBadMonitor_is_pb_is_copyable(t):
        t.assertTrue(issubclass(RemoteBadMonitor, pb.Copyable))
        t.assertTrue(issubclass(RemoteBadMonitor, pb.RemoteCopy))

    def test_translateError_transforms_ConflictError(t):
        traceback = Mock(spec_set=["_p_oid"])

        @translateError
        def raise_conflict_error():
            raise ConflictError("message", traceback)

        with t.assertRaises(RemoteConflictError):
            raise_conflict_error()

    def test_translateError_transforms_Exception(t):
        @translateError
        def raise_error():
            raise Exception("message", "traceback")

        with t.assertRaises(RemoteException):
            raise_error()
