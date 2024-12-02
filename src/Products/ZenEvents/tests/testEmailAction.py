##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from mock import Mock, patch

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.actions import EmailAction


class TestEmailAction(BaseTestCase):

    @patch("Products.ZenModel.actions.log")
    @patch("Products.ZenModel.actions.sendEmail")
    @patch("Products.ZenModel.actions.processTalSource")
    def testExecuteBatchSocketError(self, mockedProcessTalSource, mockedSendEmail, mockedLog):
        """ ZEN-33834 case """
        mockedSendEmail.return_value = (None, "<class 'socket.error'> - [Errno 4] Interrupted system call")
        mockedProcessTalSource.return_value = ""
        email_action = EmailAction()
        email_action.setupAction = Mock()
        email_action._targetsByTz = Mock(return_value={"": set()})
        email_action._adjustToTimezone = Mock()
        email_action._signalToContextDict = Mock(return_value={
            "evt": Mock(details={"recipients": "test1@test.test, test2@test.test"})
        })
        keys = ["Subject", "From", "To", "Date"]
        email_action._encodeBody = Mock(return_value=dict.fromkeys(keys))
        email_action._stripTags = Mock()
        email_action.stripBodyTags = Mock()
        keys = ["clear_subject_format", "clear_body_format", "body_content_type", "host", "port", "user", "password",
                "useTls", "email_from"]
        notification, signal, targets = (Mock(content=dict.fromkeys(keys)), Mock(), set())
        email_action.executeBatch(notification, signal, targets)
        self.assertEqual(mockedLog.info.call_count, 3)
        self.assertIn("try again", str(mockedLog.info.mock_calls[0]))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestEmailAction))
    return suite
