##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from unittest import TestCase


class BaseTestCase(TestCase):
    def setUp(t):
        logging.disable(logging.CRITICAL)

    def tearDown(t):
        logging.disable(logging.NOTSET)
