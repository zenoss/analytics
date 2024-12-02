#!/usr/bin/env python

from unittest import TestCase

from twisted.spread.pb import RemoteError
from twisted.python.failure import Failure

from Products.ZenUtils.Exceptions import (
    resolveException, ZenResolveExceptionError
)


class resolveExceptionTests(TestCase):

    def test_resolveException(self):
        exception = RuntimeError('genric exception')
        failure = Failure(exception)
        out = resolveException(failure)
        self.assertEqual(out, exception)

    def test_alternate_failure_constructor(self):
        failure = Failure(exc_value="boom", exc_type=RuntimeError, exc_tb=[])
        out = resolveException(failure)
        expected = RuntimeError('boom')
        self.assertIsInstance(out, RuntimeError)
        self.assertEqual(out.args, expected.args)

    def test_handles_twisted_spread_pb_RemoteError(self):
        exception = RemoteError('remoteType', 'value', 'remoteTraceback')
        failure = Failure(exception)
        out = resolveException(failure)
        self.assertIsInstance(out, RemoteError)
        self.assertEqual(out, exception)

    def test_wraps_invalid_failure_objects(self):
        failure = {'i am': 'not a', 'valid': 'failure'}
        out = resolveException(failure)
        expected = ZenResolveExceptionError(failure)
        self.assertIsInstance(out, ZenResolveExceptionError)
        self.assertEqual(out.args, expected.args)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(resolveExceptionTests))
    return suite
