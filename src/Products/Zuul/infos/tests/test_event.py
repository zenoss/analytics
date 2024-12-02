##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.infos.event import EventCompatDetailInfo
from mock import patch


class EventCompatDetailInfoTest(BaseTestCase):

    def afterSetUp(self):
        super(EventCompatDetailInfoTest, self).afterSetUp()

    @patch("Products.Zuul.infos.event.EventCompatDetailInfo.__init__")
    def test_log(self, mock_ecdi_init):
        '''Ensure that the log property returns the un-altered values
        of the properties in the expected format:
        a list of tuples like [(user_name, created_time, message), ...]
        '''
        # Mock the __init__ method, we are only testing the log property
        mock_ecdi_init.return_value = None
        ecdi = EventCompatDetailInfo()

        ecdi._event_summary = {
            'notes': [{
                'created_time': 999,
                'user_name': 'admin',
                'message': '<p>tracer-1</p>',
                'user_uuid': '77a74184-5680-4cdf-91df-3a717af90b25',
                'uuid': '0242ac11-0021-bc8e-11e7-628668ff70b9'
            }, {
                'created_time': 777,
                'user_name': 'admin',
                'message': '<p>tracer-3</p>',
                'user_uuid': '77a74184-5680-4cdf-91df-3a717af90b25',
                'uuid': '0242ac11-0021-bc8e-11e7-61ba7383fac0'
            }, {
                'created_time': 888,
                'user_name': 'admin',
                'message': '<p>tracer-2</p>',
                'user_uuid': '77a74184-5680-4cdf-91df-3a717af90b25',
                'uuid': '0242ac11-0021-bc8e-11e7-619c55fac639'
            }]}

        # Output events in descending order by timestamp
        expected_output = [
            ('admin', 999, '<p>tracer-1</p>'),
            ('admin', 888, '<p>tracer-2</p>'),
            ('admin', 777, '<p>tracer-3</p>')
        ]

        self.assertEqual(
            ecdi.log,
            expected_output
        )


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(EventCompatDetailInfoTest),))


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
