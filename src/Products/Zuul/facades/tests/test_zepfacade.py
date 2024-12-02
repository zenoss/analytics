##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
import zope.component
import zope.component.event
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.ZenUtils.guid import generate
from Products.Zuul.interfaces import *
from Products.Zuul import getFacade
from Products.ZenEvents.ZenEventClasses import Unknown


class TestZepFacade(ZuulFacadeTestCase):

    def afterSetUp(self):
        super(TestZepFacade, self).afterSetUp()
        
        self.eventClassId = "App"
        self.dmd.Events.createOrganizer(self.eventClassId)
        self.zep = getFacade('zep', self.dmd)

    def test_interfaces(self):
        pass

    def test_create_event_mapping(self):
        eventdata = [dict(eventClassKey="abc123",
                          evid = generate(),
                          eventClass={'text': Unknown})]
        msg, url = self.zep.createEventMapping(eventdata, "/" + self.eventClassId)
        # verify the msg
        self.assertTrue('Created 1 event mapping' in msg)

    def test_invalid_event_class(self):
        eventdata = [dict(eventClassKey="abc1234",
                          evid = generate(),
                          eventClass={'text': "/Pepe"})]
        msg, url = self.zep.createEventMapping(eventdata, "/" + self.eventClassId)
        # verify the msg
        self.assertTrue('is not of the class Unknown' in msg)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestZepFacade),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
