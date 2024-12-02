##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from mock import patch

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *

from Products.ZenModel.Location import Location
from ZenModelBaseTest import ZenModelBaseTest


class TestLocation(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestLocation, self).afterSetUp()
        # Monkeypatch Location since it doesn't have access to page templates
        # via acquisition
        Location.mapTooltip = lambda *x:'PAGE TEMPLATE'

    def beforeTearDown(self):
        # Remove the monkeypatch
        del Location.mapTooltip
        super(TestLocation, self).beforeTearDown()

    @patch.object(Location, "getWorstEventSeverity", create=True)
    def testGoogleMapsData(self, getWorstEventSeverity):
        a = self.dmd.Locations.createOrganizer('A')
        a.address = 'rome, italy'
        data = a.getGeomapData()
        self.assert_(isinstance(data, list))
        addr, color, path, tpl, uid = data
        self.assertEqual(addr, 'rome, italy')
        self.assertEqual(path, '/zport/dmd/Locations/A')
        self.assertEqual(tpl, 'PAGE TEMPLATE')

        locdata = self.dmd.Locations.getChildGeomapData()
        # Make sure it's JSON
        self.assert_(isinstance(locdata, basestring))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestLocation))
    return suite


if __name__=="__main__":
    framework()
