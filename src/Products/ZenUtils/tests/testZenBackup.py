##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.ZenBackup import strip_definer

class TestDefiner(BaseTestCase):
    """Test the DEFINER stripping."""

    def test50013(self):
        input_text = \
"""foo
/*!50013 DEFINER=`user_a`@`localhost` SQL SECURITY DEFINER */
bar"""
        expected = \
"""foo

bar"""
        actual = "\n".join(strip_definer(line) for line in input_text.splitlines())
        self.assertEqual(actual, expected)

    def test50017(self):
        input_text = \
"""/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`10.175.209.87`*/ /*!50003 TRIGGER `event_summary_index_queue_insert` AFTER INSERT ON `event_summary`
FOR EACH ROW BEGIN
INSERT INTO `event_summary_index_queue` SET uuid=NEW.uuid, update_time=NEW.update_time;
END */;;"""
        expected = \
"""/*!50003 CREATE*/  /*!50003 TRIGGER `event_summary_index_queue_insert` AFTER INSERT ON `event_summary`
FOR EACH ROW BEGIN
INSERT INTO `event_summary_index_queue` SET uuid=NEW.uuid, update_time=NEW.update_time;
END */;;"""
        actual = "\n".join(strip_definer(line) for line in input_text.splitlines())
        self.assertEqual(actual, expected)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestDefiner),))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
