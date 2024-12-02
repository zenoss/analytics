##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from mock import patch

from Products.Zuul.facades import ZuulFacade
from Products.Zuul.facades.triggersfacade import TriggersFacade

from Products.ZenModel.NotificationSubscriptionWindow import (
    NotificationSubscriptionWindow
)


class TriggersFacadeTest(BaseTestCase):

    def afterSetUp(self):
        super(TriggersFacadeTest, self).afterSetUp()

    @patch('Products.Zuul.facades.triggersfacade.TriggersFacade.__init__')
    @patch.object(ZuulFacade, '_getObject')
    def test_updateWindow(self, mock_getobject, tf_init):
        # Mock the facade's init method, we are testing methods in isolation
        tf_init.return_value = None
        tf = TriggersFacade()
        # _getObject returns a NotificationSubscriptionWindow
        window = NotificationSubscriptionWindow('window_id')
        mock_getobject.return_value = window

        request_payload_data = {
            'uid': "/zport/dmd/NotificationSubscriptions/test_notification"
                   "/windows/test_schedule",
            # "2017-09-24T16:00:00+00:00" UTC, in seconds
            'start_ts': 1506268800,
            'duration': "60",
            'enabled': False,
            'repeat': "Daily"
        }

        tf.updateWindow(request_payload_data)

        # ensure mocking ZuulFacade._getObject worked
        mock_getobject.assert_called_with(request_payload_data['uid'])

        # ensure window is updated with request_payload_data
        self.assertEqual(window.start, request_payload_data['start_ts'])
        self.assertEqual(window.enabled, request_payload_data['enabled'])
        self.assertEqual(window.repeat, request_payload_data['repeat'])


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TriggersFacadeTest),))


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
