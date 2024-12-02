##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.ZenModelRM import ZenModelRM
from DateTime import DateTime


class TestZenModelRM(BaseTestCase):

    def setUp(self):
        self.this_id = 'String'
        self.zen_model_rm = ZenModelRM(id=self.this_id)

    def test_ZenModel_id(self):
        '''Ensure ZenModelRM objects id attribute
        is the id value it was created with.
        '''
        self.assertEqual(
            self.this_id,
            self.zen_model_rm.id
        )

    def test_createdTime(self):
        '''LEGACY createdTime
        returns a Zope DateTime object
        '''
        created_time = self.zen_model_rm.createdTime

        self.assertIsInstance(created_time, DateTime)

    def test_created_timestamp(self):
        '''ensure created_timestamp returns a float
        '''
        time_stamp = self.zen_model_rm.created_timestamp

        self.assertIsInstance(time_stamp, float)

    def test_create_time_stamp_backwards_compat(self):
        '''ensure create_time_stamp returns a timestamp for legacy objects
        created with a Zope DateTime object instead of timestamp
        '''
        del self.zen_model_rm._created_timestamp

        time_stamp = self.zen_model_rm.created_timestamp
        self.assertIsInstance(time_stamp, float)
