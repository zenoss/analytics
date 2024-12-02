##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from zope.event import notify

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.exceptions import BadIndexingEvent


class ModelCatalogTests(BaseTestCase):

    def test_bad_indexing_event_indexes(self):
        with self.assertRaises(BadIndexingEvent):
            notify(IndexingEvent(self.dmd.Devices, idxs="you_d_better_raise_an_error"))


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ModelCatalogTests),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')