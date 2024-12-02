##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.tests.plugins.CollectorPlugin import TestPlugin


class withimports(TestPlugin):
    def get_re(self):
        return re
