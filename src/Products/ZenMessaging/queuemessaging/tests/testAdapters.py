# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenMessaging.queuemessaging.adapters import _safestr
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class TestAdapters(BaseTestCase):
    def test_safestr(self):
        tested_string = u"text with 今導降 unicode"
        output = _safestr(tested_string)
        self.assertEqual(output, tested_string)

        tested_string = "text without unicode"
        output = _safestr(tested_string)
        self.assertEqual(output, tested_string)
