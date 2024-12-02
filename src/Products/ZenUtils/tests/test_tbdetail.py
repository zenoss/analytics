##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""runtests -m test_tbdetail -n test_log_tb Products.ZenUtils"""

from sys import exc_info
from os import stat
from shutil import rmtree
from unittest import TestCase, makeSuite
from ..tbdetail import _LOG_DIR, log_tb


class TestTbdetail(TestCase):

    def test_log_tb(self):
        """call log_tb twice to make sure it handles the case where
        $ZENHOME/log/traceback directory is already created"""
        try:
            rmtree(_LOG_DIR)
        except OSError:
            # directory doesn't exist do not try to remove it
            pass
        for i in range(2):
            try:
                self._raise()
                self.fail("raise method didn't raise")
            except Exception:
                message = log_tb(exc_info())
                path = message.split()[0]
                self.assert_(0 < stat(path).st_size, 'log file is empty')

    def _raise(self):
        """raise an exception"""
        raise Exception("Testing log_tb")


def test_suite():
    return makeSuite(TestTbdetail)
