##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import time

from datetime import datetime

from zope.interface import Interface, implementer
from Zope2.App import zcml

from Products.ZenTestCase.BaseTestCase import BaseTestCase

import Products.ZenCallHome

from Products.ZenCallHome import ICallHomeCollector
from Products.ZenCallHome.callhome import (
    CallHomeCollector,
    CallHomeData,
    EXTERNAL_ERROR_KEY,
    REPORT_DATE_KEY,
    VERSION_HISTORIES_KEY,
)
from Products.ZenCallHome.VersionHistory import (
    KeyedVersionHistoryCallHomeCollector,
    VERSION_START_KEY,
)
from Products.ZenCallHome.transport import (
    CallHome,
    CallHomeData as PersistentCallHomeData,
)


DATETIME_ISOFORMAT = "%Y-%m-%dT%H:%M:%S.%f"

TEST_DATA = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
     <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.TestCallHomeData"
               provides="Products.ZenCallHome.tests.testCallHomeGeneration.ITestCallHomeData"
               name="testdata"/>
      </configure>
"""  # noqa E501

FAILING_TEST_DATA = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
      <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.FailingTestCallHomeData"
               provides="Products.ZenCallHome.tests.testCallHomeGeneration.ITestCallHomeData"
               name="failingtestdata"/>
      </configure>
"""  # noqa E501

SIMPLE_SUCCESS_COLLECTOR = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
      <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.SimpleSuccessCollector"
               provides="Products.ZenCallHome.ICallHomeCollector"
               name="simplesuccess"/>
      </configure>
"""  # noqa E501

SIMPLE_SUCCESS_KEY = "simplesuccess"

FAST_FAIL_COLLECTOR = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
     <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.FastFailCollector"
                     provides="Products.ZenCallHome.ICallHomeCollector"
                     name="fastfail"/>
     </configure>
"""  # noqa E501

FAST_FAIL_KEY = "fastfail"

FAST_FAIL_ERROR_MESSAGE = "Fast failed at collector level"
FAILING_DATA_ERROR_MESSAGE = "Failed individual test data"

TEST_VERSION_HISTORY_COLLECTOR = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:five="http://namespaces.zope.org/five">
     <utility component="Products.ZenCallHome.tests.testCallHomeGeneration.TestVersionHistoryCollector"
                     provides="Products.ZenCallHome.IVersionHistoryCallHomeCollector"
                     name="testversionhistory"/>
     </configure>
"""  # noqa E501


class ITestCallHomeData(Interface):
    """ """

    def callHomeData(self):
        """ """


@implementer(ITestCallHomeData)
class TestCallHomeData(object):
    def callHomeData(self):
        yield "test", "test"


class FailingTestDataException(Exception):
    pass


@implementer(ITestCallHomeData)
class FailingTestCallHomeData(object):
    def callHomeData(self):
        raise FailingTestDataException(FAILING_DATA_ERROR_MESSAGE)


@implementer(ICallHomeCollector)
class SimpleSuccessCollector(CallHomeCollector):
    """Default success collector as a control variable."""

    def __init__(self):
        super(SimpleSuccessCollector, self).__init__(ITestCallHomeData)
        self._key = SIMPLE_SUCCESS_KEY


class FastFailTestException(Exception):
    pass


@implementer(ICallHomeCollector)
class FastFailCollector(CallHomeCollector):
    """Default success collector as a control variable."""

    def __init__(self):
        super(FastFailCollector, self).__init__(ITestCallHomeData)
        self._key = FAST_FAIL_KEY

    def generateData(self):
        raise FastFailTestException(FAST_FAIL_ERROR_MESSAGE)


TEST_VERSION_HISTORY_ENTITY = "testentity"
TEST_VERSION_1 = "testversion1"
TEST_VERSION_2 = "testversion2"
TEST_CURRENT_VERSION = TEST_VERSION_1


def returnHistory():
    return TEST_CURRENT_VERSION


class TestVersionHistoryCollector(KeyedVersionHistoryCallHomeCollector):
    """ """

    def __init__(self):
        super(TestVersionHistoryCollector, self).__init__(
            TEST_VERSION_HISTORY_ENTITY, {}
        )

    def getCurrentVersion(self, dmd, callHomeData):
        return returnHistory()


class testCallHomeGeneration(BaseTestCase):
    def afterSetUp(self):
        super(testCallHomeGeneration, self).afterSetUp()
        zcml.load_config("meta.zcml", Products.ZenCallHome)
        zcml.load_config("configure.zcml", Products.ZenCallHome)

    def beforeTearDown(self):
        super(testCallHomeGeneration, self).beforeTearDown()

    def checkForExistingCallHomeData(self):
        try:
            self.dmd.callHome
            self.fail("New zodb instance should not have callhome data")
        except AttributeError:
            pass

    def testCallHomeCollectorFailure(self):
        # check current version of report (should be empty)
        self.checkForExistingCallHomeData()

        # register bad acting callhome collector via zcml (or directly)
        zcml.load_string(TEST_DATA)
        zcml.load_string(SIMPLE_SUCCESS_COLLECTOR)
        zcml.load_string(FAST_FAIL_COLLECTOR)

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()

        # make sure report has data from default collectors and
        # successful collector, but not the failing collector
        self.assertTrue(SIMPLE_SUCCESS_KEY in data)
        self.assertTrue(FAST_FAIL_KEY not in data)
        self.assertTrue("Zenoss App Data" in data)
        self.assertTrue(EXTERNAL_ERROR_KEY in data)
        self.assertEquals(
            FAST_FAIL_ERROR_MESSAGE, data[EXTERNAL_ERROR_KEY][0]["exception"]
        )

    def testConstituentDataFailure(self):
        # check current version of report (should be empty?)
        self.checkForExistingCallHomeData()

        # register bad acting callhome collector via zcml (or directly)
        zcml.load_string(FAILING_TEST_DATA)
        zcml.load_string(TEST_DATA)
        zcml.load_string(SIMPLE_SUCCESS_COLLECTOR)

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()

        # make sure report has basic values even though part failed.
        # specifically make sure that simple success section is present
        # and that the successful data entry is there and the failed
        # entry is not
        self.assertTrue("Zenoss App Data" in data)
        self.assertTrue(SIMPLE_SUCCESS_KEY in data)
        successData = data[SIMPLE_SUCCESS_KEY]
        self.assertTrue("test" in successData)
        self.assertTrue(EXTERNAL_ERROR_KEY in data)
        self.assertEquals(
            FAILING_DATA_ERROR_MESSAGE,
            data[EXTERNAL_ERROR_KEY][0]["exception"],
        )

    def testPayloadGeneration(self):
        # check current version of report (should be empty)
        self.checkForExistingCallHomeData()

        # call callhome scripting
        beforeReportGeneration = datetime.utcnow()
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()
        afterReportGeneration = datetime.utcnow()

        time.sleep(1)

        # Unfortunately the cycler code can't be disentagled
        # from itself for testability so we have to mimic it
        # for this test case.
        # What happens is that CallHomeCycler
        # kicks off the callhome script (callhome.py)
        # and takes the process output as a string
        # and stores it in the callhome object
        # in zodb (dmd.callHome). In callhome.py you can
        # see that the Main class spits out the
        # json.dumps of the output of CallHomeData.getData.
        self.dmd.callHome = PersistentCallHomeData()
        self.dmd.callHome.metrics = json.dumps(data)

        # create the actual payload that will be sent
        beforePayloadGeneration = datetime.utcnow()
        payloadGenerator = CallHome(self.dmd)
        payload = payloadGenerator.get_payload(doEncrypt=False)
        afterPayloadGeneration = datetime.utcnow()

        # decrypt payload and reconstitute object
        payloadObj = json.loads(payload)

        # make sure payload has the required fields
        self.assertTrue("product" in payloadObj)
        self.assertTrue("uuid" in payloadObj)
        self.assertTrue("symkey" in payloadObj)
        self.assertTrue("metrics" in payloadObj)

        # reconstitute metrics obj & make sure send date is present
        # and has a valid time
        metricsObj = json.loads(payloadObj["metrics"])
        self.assertTrue("Send Date" in metricsObj)
        sendDateDT = datetime.strptime(
            metricsObj["Send Date"], DATETIME_ISOFORMAT
        )
        reportDateDT = datetime.strptime(
            metricsObj["Report Date"], DATETIME_ISOFORMAT
        )
        self.assertTrue(reportDateDT < sendDateDT)
        self.assertTrue(
            beforeReportGeneration <= reportDateDT <= afterReportGeneration
        )
        self.assertTrue(
            beforePayloadGeneration <= sendDateDT <= afterPayloadGeneration
        )

    def testZenossVersionHistory(self):
        # check current version of report (should be empty?)
        self.checkForExistingCallHomeData()

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()
        reportDate = data[REPORT_DATE_KEY]
        zenossVersion = data["Zenoss App Data"]["Zenoss"]

        # make sure report has Zenoss version history record
        self.assertTrue(VERSION_HISTORIES_KEY in data)
        versionHistories = data[VERSION_HISTORIES_KEY]
        self.assertTrue("Zenoss" in versionHistories)
        versionHistory = versionHistories["Zenoss"]
        self.assertTrue(zenossVersion in versionHistory)
        historyRecord = versionHistory[zenossVersion]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(reportDate, historyRecord[VERSION_START_KEY])

    def testSavedVersionHistory(self):
        # check current version of report (should be empty)
        self.checkForExistingCallHomeData()

        # set up test version history collector
        zcml.load_string(TEST_VERSION_HISTORY_COLLECTOR)

        # generate callhome
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()
        firstReportDate = data[REPORT_DATE_KEY]

        time.sleep(1)

        # make sure version history record is present and correct
        self.assertTrue(VERSION_HISTORIES_KEY in data)
        versionHistories = data[VERSION_HISTORIES_KEY]
        self.assertTrue(TEST_VERSION_HISTORY_ENTITY in versionHistories)
        versionHistory = versionHistories[TEST_VERSION_HISTORY_ENTITY]
        self.assertTrue(TEST_VERSION_1 in versionHistory)
        historyRecord = versionHistory[TEST_VERSION_1]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(firstReportDate, historyRecord[VERSION_START_KEY])

        # The cycler code is where the saving of
        # callhome data in ZODB occurs. We'll have
        # to mimic that again here.
        self.dmd.callHome = PersistentCallHomeData()
        self.dmd.callHome.metrics = json.dumps(data)

        # update the version history
        global TEST_CURRENT_VERSION
        TEST_CURRENT_VERSION = TEST_VERSION_2

        # generate callhome again
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()
        secondReportDate = data[REPORT_DATE_KEY]

        # make sure a second version history record exists
        self.assertTrue(VERSION_HISTORIES_KEY in data)
        versionHistories = data[VERSION_HISTORIES_KEY]
        self.assertTrue(TEST_VERSION_HISTORY_ENTITY in versionHistories)
        versionHistory = versionHistories[TEST_VERSION_HISTORY_ENTITY]
        self.assertTrue(TEST_VERSION_1 in versionHistory)
        historyRecord = versionHistory[TEST_VERSION_1]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(firstReportDate, historyRecord[VERSION_START_KEY])
        self.assertTrue(TEST_VERSION_2 in versionHistory)
        historyRecord = versionHistory[TEST_VERSION_2]
        self.assertTrue(VERSION_START_KEY in historyRecord)
        self.assertEquals(secondReportDate, historyRecord[VERSION_START_KEY])

    def testSendMethod(self):
        # check current version of report (should be empty)
        self.checkForExistingCallHomeData()

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()

        # Unfortunately the cycler code can't be disentagled
        # from itself for testability so we have to mimic it
        # for this test case.
        # What happens is that CallHomeCycler
        # kicks off the callhome script (callhome.py)
        # and takes the process output as a string
        # and stores it in the callhome object
        # in zodb (dmd.callHome). In callhome.py you can
        # see that the Main class spits out the
        # json.dumps of the output of CallHomeData.getData.
        self.dmd.callHome = PersistentCallHomeData()
        self.dmd.callHome.metrics = json.dumps(data)

        # create the actual payload that will be sent
        payloadGenerator = CallHome(self.dmd)
        payload = payloadGenerator.get_payload(doEncrypt=False)

        # reconstitute object
        payloadObj = json.loads(payload)

        # reconstitute metrics obj & make sure send date is present
        # and has a valid time
        metricsObj = json.loads(payloadObj["metrics"])
        self.assertTrue("Send Method" in metricsObj)
        self.assertEquals("directpost", metricsObj["Send Method"])

        # Fetch the payload the browserjs way
        payloadGenerator = CallHome(self.dmd)
        payload = payloadGenerator.get_payload(
            method="browserjs", doEncrypt=False
        )

        # reconstitute object
        payloadObj = json.loads(payload)

        # reconstitute metrics obj & make sure send date is present
        # and has a valid time
        metricsObj = json.loads(payloadObj["metrics"])
        self.assertTrue("Send Method" in metricsObj)
        self.assertEquals("browserjs", metricsObj["Send Method"])

    def testGenerateReportWithEmptyMetricsField(self):
        # Make sure that an empty metrics field
        # does not cause failure on subsequent
        # callhome generation calls. First
        # handle None value for metrics
        self.dmd.callHome = PersistentCallHomeData()
        self.dmd.callHome.metrics = None

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()  # noqa F841

        # Then handle empty string value
        self.dmd.callHome.metrics = ""

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()  # noqa F841

        # Then handle whitespace-only string value
        self.dmd.callHome.metrics = "   "

        # call callhome scripting
        chd = CallHomeData(self.dmd, True)
        data = chd.getData()  # noqa F841

    #
    # UNFORTUNATELY CANNOT EASILY UNIT TEST TIMEOUTS BECAUSE
    # OF THE CROSS-PROCESS STEPS
    #
    # def testTimeOutCallHomeCollector(self):
    #


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(testCallHomeGeneration))
    return suite
