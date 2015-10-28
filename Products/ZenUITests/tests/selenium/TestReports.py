#!/usr/bin/python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# Contained below is the class that tests elements located under
# the "Reports" Browse By subheading.
#
# Adam Modlin, Nate Avers and Noel Brockett
#

import unittest

from util.selTestUtils import TimeoutError, do_command_byname, getByValue

from SelTestBase import SelTestBase

class TestReports(SelTestBase):
    """Defines an object that runs tests under the Reports heading"""

    def _addTestReportOrganizer(self):
        self.waitForElement("link=Reports")
        self.selenium.click("link=Reports")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=testingString"):
            self._deleteTestReportOrganizer()
        self.addDialog(addType="ReportClasslistaddReportClass", new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteTestReportOrganizer(self):
        self.waitForElement("link=Reports")
        self.selenium.click("link=Reports")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog(deleteType="ReportClasslistdeleteReportClasses", form_name="reportClassForm")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
    
    def testReportOrganizer(self):
        """Run tests on the Reports page"""
        
        self.addDevice('localhost')
        self._addTestReportOrganizer()
        #Selects All 
        self.waitForElement("id=selectall_0")
        self.selenium.click("id=selectall_0")
        do_command_byname(self.selenium, "assertChecked", "ids:list")
        self.selenium.click("id=selectnone_0")
        do_command_byname(self.selenium, "assertNotChecked", "ids:list")
        
        #Checks to make sure that the added device is listed in the Device Reports/All devices
        self.selenium.click("link=Device Reports")
        self.waitForElement("link=All Devices")
        self.selenium.click("link=All Devices")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertElementPresent', 
                ['link=localhost'])

        #Checks to make sure that the added device is listed in the Device Reports/New devices
        self.selenium.click("link=Device Reports") 
        self.waitForElement("link=New Devices")
        self.selenium.click("link=New Devices")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertElementPresent', 
                ['link=localhost'])


        self._deleteTestReportOrganizer()
        for devicename in self.devicenames:
                self.deleteDevice(devicename)
            
if __name__ == "__main__":
        unittest.main()
