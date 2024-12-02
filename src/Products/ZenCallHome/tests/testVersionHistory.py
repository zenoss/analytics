##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from datetime import datetime, timedelta

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenCallHome.callhome import REPORT_DATE_KEY
from Products.ZenCallHome.VersionHistory import (
    VERSION_START_KEY,
    VERSION_HISTORIES_KEY,
    KeyedVersionHistoryCallHomeCollector,
)


TEST_ENTITY = "testentity"

HISTPROP1_KEY = "histprop1"
PROP1_TARGET_KEY = "prop1"
HISTPROP1_VALUE = "testvalue1"
HISTPROP1_SECONDVALUE = "testvalue1_2"
HISTPROP2_KEY = "app.histprop2"
PROP2_TARGET_KEY = "prop2"
HISTPROP2_VALUE = "testvalue2"
MISSING_PROP_KEY = "missing.prop.key"
MISSING_TARGET_KEY = "missingprop"
TEST_VERSION_KEY = "app.testversion"
TEST_VERSION_VALUE_1 = "versionstring_1"
TEST_VERSION_VALUE_2 = "versionstring_2"
REPORT_DATE_VALUE_1 = datetime.utcnow()
REPORT_DATE_VALUE_2 = REPORT_DATE_VALUE_1 + timedelta(days=1)
REPORT_DATE_VALUE_3 = REPORT_DATE_VALUE_2 + timedelta(days=1)
REPORT_DATE_VALUE_1 = REPORT_DATE_VALUE_1.isoformat()
REPORT_DATE_VALUE_2 = REPORT_DATE_VALUE_2.isoformat()
REPORT_DATE_VALUE_3 = REPORT_DATE_VALUE_3.isoformat()


def createTestCallHomeData():
    return {
        "histprop1": "testvalue1",
        "app": {
            "histprop2": "testvalue2",
            "testversion": TEST_VERSION_VALUE_1,
        },
        REPORT_DATE_KEY: REPORT_DATE_VALUE_1,
    }


TEST_KEY_MAP = {
    HISTPROP1_KEY: PROP1_TARGET_KEY,
    HISTPROP2_KEY: PROP2_TARGET_KEY,
}


class TestVersionHistoryCollector(KeyedVersionHistoryCallHomeCollector):
    """ """

    def __init__(self):
        super(TestVersionHistoryCollector, self).__init__(
            TEST_ENTITY, TEST_KEY_MAP
        )

    def getCurrentVersion(self, dmd, callHomeData):
        return self.getKeyedValue(TEST_VERSION_KEY, callHomeData)


class testVersionHistory(BaseTestCase):
    def afterSetUp(self):
        super(testVersionHistory, self).afterSetUp()
        # zcml.load_config('meta.zcml', Products.ZenCallHome)
        # zcml.load_config('configure.zcml', Products.ZenCallHome)

    def beforeTearDown(self):
        super(testVersionHistory, self).beforeTearDown()

    def testVersionHistory(self):
        # create dummy callhome data
        testCallHomeData = createTestCallHomeData()

        # create the collector
        collector = TestVersionHistoryCollector()

        # insert version history
        collector.addVersionHistory(self.dmd, testCallHomeData)

        # Validate that:
        #    VersionHistory is present
        #    The entity is present in the version history
        #    There is a version record
        #    Version start time has the right value
        #    The record has the right properties
        self.assertTrue(VERSION_HISTORIES_KEY in testCallHomeData)
        versionHistories = testCallHomeData[VERSION_HISTORIES_KEY]
        self.assertTrue(TEST_ENTITY in versionHistories)
        versionHistory = versionHistories[TEST_ENTITY]
        self.assertTrue(TEST_VERSION_VALUE_1 in versionHistory)
        historyRecord = versionHistory[TEST_VERSION_VALUE_1]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(
            REPORT_DATE_VALUE_1, historyRecord[VERSION_START_KEY]
        )
        self.assertTrue(PROP1_TARGET_KEY in historyRecord)
        self.assertEquals(HISTPROP1_VALUE, historyRecord[PROP1_TARGET_KEY])
        self.assertTrue(PROP2_TARGET_KEY in historyRecord)
        self.assertEquals(HISTPROP2_VALUE, historyRecord[PROP2_TARGET_KEY])

        # Update the report date to simulate a new callhome
        # without a version change, even though some
        # property values may change
        testCallHomeData[REPORT_DATE_KEY] = REPORT_DATE_VALUE_2
        testCallHomeData[HISTPROP1_KEY] = HISTPROP1_SECONDVALUE

        # Check for need to update version history
        collector.addVersionHistory(self.dmd, testCallHomeData)

        # No version change means that there should
        # still only be one version record with
        # the previous date and the previous values
        self.assertTrue(VERSION_HISTORIES_KEY in testCallHomeData)
        versionHistories = testCallHomeData[VERSION_HISTORIES_KEY]
        self.assertTrue(TEST_ENTITY in versionHistories)
        versionHistory = versionHistories[TEST_ENTITY]
        self.assertEquals(1, len(versionHistory.keys()))
        self.assertTrue(TEST_VERSION_VALUE_1 in versionHistory)
        historyRecord = versionHistory[TEST_VERSION_VALUE_1]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(
            REPORT_DATE_VALUE_1, historyRecord[VERSION_START_KEY]
        )
        self.assertTrue(PROP1_TARGET_KEY in historyRecord)
        self.assertEquals(HISTPROP1_VALUE, historyRecord[PROP1_TARGET_KEY])
        self.assertTrue(PROP2_TARGET_KEY in historyRecord)
        self.assertEquals(HISTPROP2_VALUE, historyRecord[PROP2_TARGET_KEY])

        # Update the version and report date.
        testCallHomeData[REPORT_DATE_KEY] = REPORT_DATE_VALUE_3
        testCallHomeData["app"]["testversion"] = TEST_VERSION_VALUE_2

        # Update the version history
        collector.addVersionHistory(self.dmd, testCallHomeData)

        # There should now be two version history records.
        # The second one should have the date value and
        # the updated property value.
        self.assertTrue(VERSION_HISTORIES_KEY in testCallHomeData)
        versionHistories = testCallHomeData[VERSION_HISTORIES_KEY]
        self.assertTrue(TEST_ENTITY in versionHistories)
        versionHistory = versionHistories[TEST_ENTITY]
        self.assertEquals(2, len(versionHistory.keys()))
        self.assertTrue(TEST_VERSION_VALUE_2 in versionHistory)
        historyRecord = versionHistory[TEST_VERSION_VALUE_2]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(
            REPORT_DATE_VALUE_3, historyRecord[VERSION_START_KEY]
        )
        self.assertTrue(PROP1_TARGET_KEY in historyRecord)
        self.assertEquals(
            HISTPROP1_SECONDVALUE, historyRecord[PROP1_TARGET_KEY]
        )
        self.assertTrue(PROP2_TARGET_KEY in historyRecord)
        self.assertEquals(HISTPROP2_VALUE, historyRecord[PROP2_TARGET_KEY])


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(testVersionHistory))
    return suite
