##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
from datetime import datetime
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.Zuul.infos.triggers import NotificationWindowInfo
from Products.ZenModel.NotificationSubscriptionWindow import (
    NotificationSubscriptionWindow
)


class NotificationWindowInfoTest(BaseTestCase):

    def afterSetUp(self):
        super(NotificationWindowInfoTest, self).afterSetUp()

    def test_start_time(self):
        '''Ensure that the notification window infos
        returns the attributes expected by the UI
        '''

        expected_start_ts = 1506243600
        dttm = datetime.fromtimestamp(expected_start_ts)
        expected_dt = dttm.date().strftime("%m/%d/%Y")
        expected_tm = dttm.time().strftime("%H:%M")

        window = NotificationSubscriptionWindow('window_id')
        setattr(window, 'start', expected_start_ts)

        window_info = NotificationWindowInfo(window)

        self.assertEqual(window_info.start_ts, expected_start_ts)

        # ensure original date/time behavior for backwards compatibility
        self.assertEqual(window_info.start, expected_dt)
        self.assertEqual(window_info.starttime, expected_tm)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(NotificationWindowInfoTest),
    ))


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
