##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2009, 2021 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import dateutil.tz as tz

from time import mktime, time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from ZODB.POSException import ConflictError

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow, DAY_SECONDS
from Products.ZenUtils import Time
# Note: The new messaging code inteferes with FakeRequest operations,
#      as the adapter machinery doesn't load
#from Products.ZenUtils.FakeRequest import FakeRequest


# Note: These defaults can be overridden by the user, but we only need an
#       example set to test.
state_Production=1000
state_Pre_Production=500
state_Test=400
state_Maintenance=300
state_Decommissioned=-1

stateNames = {
    state_Production:'Production',
    state_Pre_Production:'Pre-Production',
    state_Test:'Test',
    state_Maintenance:'Mainetenance',
    state_Decommissioned:'Decommissioned',
}

class TestMaintenanceWindows(ZenModelBaseTest):

    def testUTCMaintenanceWindows(self):
        m = MaintenanceWindow('tester')
        m.dmd = self.dmd
        tzInstance = tz.tzutc()

        def getLocalizedTimestamp(year, month, day, hour, minutes, seconds):
            localizedExpectedDateTime = datetime(year, month, day, hour, minutes, seconds, tzinfo=tzInstance)
            return Time.awareDatetimeToTimestamp(localizedExpectedDateTime)

        t = getLocalizedTimestamp(2006, 1, 29, 10, 45, 12)
        P = 60*60*2
        # set(start, duration, repeat, enabled=True)
        m.set(t, P, m.NEVER)
        self.assert_(m.next() == None)
        m.set(t, P, m.DAILY)
        c = getLocalizedTimestamp(2006, 1, 30, 10, 45, 12)
        self.assert_(m.next(t + P + 1) == c)
        m.set(t, P, m.WEEKLY)
        c = getLocalizedTimestamp(2006, 2, 5, 10, 45, 12)
        self.assert_(m.next(t + 1) == c)
        m.set(t - DAY_SECONDS, P, m.EVERY_WEEKDAY)
        c = getLocalizedTimestamp(2006, 1, 30, 10, 45, 12)
        self.assert_(m.next(t) == c)
        m.set(t, P, m.MONTHLY)
        c = getLocalizedTimestamp(2006, 2, 28, 10, 45, 12)
        self.assert_(m.next(t+1) == c)
        t2 = getLocalizedTimestamp(2005, 12, 31, 10, 45, 12)
        m.set(t2, P, m.MONTHLY)
        c = getLocalizedTimestamp(2006, 1, 31, 10, 45, 12)
        c2 = getLocalizedTimestamp(2006, 2, 28, 10, 45, 12)
        self.assert_(m.next(t2+1) == c)
        self.assert_(m.next(c+1) == c2)
        c = getLocalizedTimestamp(2006, 2, 5, 10, 45, 12)
        m.set(t, P, m.NTHWDAY)
        self.assert_(m.next(t+1) == c)
        c = getLocalizedTimestamp(2006, 1, 31, 10, 45, 12)
        m.set(t, P, m.NTHWDAY, 'Tuesday', 'Last')
        self.assert_(m.next(t+1) == c)
        c = getLocalizedTimestamp(2006, 2, 19, 10, 45, 12)
        m.set(t, P, m.NTHWDAY, 'Sunday', '3rd')
        self.assert_(m.next(t+1) == c)
        c = getLocalizedTimestamp(2006, 2, 22, 10, 45, 12)
        m.set(t, P, m.NTHWDAY, 'Wednesday', 'Last')
        self.assert_(m.next(t+1) == c)

        c = getLocalizedTimestamp(2006, 3, 13, 10, 45, 12)
        n = getLocalizedTimestamp(2006, 3, 6, 10, 45, 12)
        m.set(t, P, m.NTHWDAY, 'Monday', '2nd')
        self.assert_(m.next(n) == c)

        c = getLocalizedTimestamp(2006, 3, 29, 10, 45, 12)
        n = getLocalizedTimestamp(2006, 3, 6, 10, 45, 12)
        m.set(t, P, m.NTHWDAY, 'Wednesday', 'Last')
        self.assert_(m.next(n) == c)

        c = getLocalizedTimestamp(2007, 1, 8, 10, 45, 12)
        n = getLocalizedTimestamp(2007, 1, 2, 10, 45, 12)
        m.set(t, P, m.NTHWDAY, 'Monday', '2nd')
        self.assert_(m.next(n) == c)


        # DST
        FSOTM_Map = {
            # DST day      following first sunday of the month
            (2008, 3, 9):  datetime(2008, 4, 6),
            (2008, 11, 2): datetime(2008, 12, 7),
            }
        for (yy, mm, dd), sunday in FSOTM_Map.items():
            duration = 3*60
            tt = getLocalizedTimestamp(yy, mm, dd, 12, 10, 9)
            m.set(tt, duration, m.DAILY)
            c = getLocalizedTimestamp(yy, mm, dd + 1, 12, 10, 9)
            self.assert_(m.next(tt + duration) == c)

            m.set(tt, duration, m.WEEKLY)
            c = getLocalizedTimestamp(yy, mm, dd + 7, 12, 10, 9)
            self.assert_(m.next(tt + duration) == c)

            m.set(tt, duration, m.EVERY_WEEKDAY)
            c = getLocalizedTimestamp(yy, mm, dd + 1, 12, 10, 9)
            self.assert_(m.next(tt + duration) == c)

            m.set(tt, duration, m.NTHWDAY)
            date = sunday + timedelta(hours=12, minutes=10, seconds=9)
            c = getLocalizedTimestamp(date.year, date.month, date.day, date.hour, date.minute, date.second)
            self.assert_(m.next(tt + duration) == c)

            # DST: check that a 3-hour range ends at the proper time
            tt = getLocalizedTimestamp(yy, mm, dd, 0, 10, 9)
            m.set(tt, duration, m.DAILY)
            m.started = tt
            c = getLocalizedTimestamp(yy, mm, dd, 3, 10, 8)
            self.assert_(m.nextEvent(tt) == c)
            m.started = None

        # skips
        m.skip = 2
        m.set(t, P, m.DAILY)
        c = getLocalizedTimestamp(2006, 1, 31, 10, 45, 12)
        self.assert_(m.next(t + 1) == c)

        m.set(t, P, m.WEEKLY)
        c = getLocalizedTimestamp(2006, 2, 12, 10, 45, 12)
        self.assert_(m.next(t + 1) == c)

        m.set(t, P, m.MONTHLY)
        c = getLocalizedTimestamp(2006, 3, 29, 10, 45, 12)
        self.assert_(m.next(t + 1) == c)

        m.set(t - DAY_SECONDS * 2, P, m.EVERY_WEEKDAY)
        c = getLocalizedTimestamp(2006, 1, 31, 10, 45, 12)
        self.assert_(m.next(t + 1) == c)

        c = getLocalizedTimestamp(2006, 3, 5, 10, 45, 12)
        m.set(t, P, m.NTHWDAY)
        self.assert_(m.next(t+1) == c)

        m1 = MaintenanceWindow('t1')
        m2 = MaintenanceWindow('t2')
        t = getLocalizedTimestamp(2006, 1, 29, 10, 45, 12)
        duration = 1
        m1.set(t, duration, m.NEVER)
        m2.set(t + duration * 60, duration, m.NEVER)
        m1.started = t
        # ending of m1 should be < start of m2
        self.assert_(m1.nextEvent(t + 1) < m2.nextEvent(t + 1))

        #r = FakeRequest()
        r = None
        startDttm = 1138531500
        m.manage_editMaintenanceWindow(
                                         startDate='01/29/2006',
                                         startHours='10',
                                         startMinutes='45',
                                         startDateTime=str(startDttm),
                                         durationDays='1',
                                         durationHours='1',
                                         durationMinutes='1',
                                         repeat='Weekly',
                                         startProductionState=state_Maintenance,
                                         enabled=True,
                                         REQUEST=r)

        #self.assert_('message' in r)
        #self.assert_(r['message'] == 'Saved Changes')
        self.assertEqual(m.start, startDttm)
        self.assert_(m.duration == 24*60+61)
        self.assert_(m.repeat == 'Weekly')
        self.assert_(m.startProductionState == state_Maintenance)
    
    def testTimezonedWindows(self):
        m = MaintenanceWindow('tester')
        m.dmd = self.dmd
        tzName = 'Europe/Kiev'
        tzInstance = tz.gettz(tzName)

        def getLocalizedTimestamp(year, month, day, hour, minutes):
            localizedExpectedDateTime = datetime(year, month, day, hour, minutes, tzinfo=tzInstance)
            return Time.awareDatetimeToTimestamp(localizedExpectedDateTime)

        startTime = getLocalizedTimestamp(2021, 2, 19, 15, 0)
        duration = 60*60*2

        m.set(startTime, duration, m.NEVER, timezone=tzName)
        self.assertEqual(m.next(), None)

        m.set(startTime, duration, m.DAILY, timezone=tzName)
        expectedTimestamp = getLocalizedTimestamp(2021, 2, 20, 15, 0)
        self.assertEqual(m.next(startTime + duration + 1), expectedTimestamp)

        m.set(startTime, duration, m.WEEKLY, timezone=tzName)
        expectedTimestamp = getLocalizedTimestamp(2021, 2, 26, 15, 0)
        self.assertEqual(m.next(startTime + 1), expectedTimestamp)

        m.set(startTime, duration, m.EVERY_WEEKDAY)
        expectedTimestamp = getLocalizedTimestamp(2021, 2, 22, 15, 0)
        self.assertEqual(m.next(startTime), expectedTimestamp)

        m.set(startTime, duration, m.MONTHLY, timezone=tzName)
        expectedTimestamp = getLocalizedTimestamp(2021, 3, 19, 15, 0)
        self.assertEqual(m.next(startTime+1), expectedTimestamp)

        t2 = getLocalizedTimestamp(2020, 12, 31, 15, 0)
        m.set(t2, duration, m.MONTHLY, timezone=tzName)
        expectedTimestamp_1 = getLocalizedTimestamp(2021, 1, 31, 15, 0)
        expectedTimestamp_2 = getLocalizedTimestamp(2021, 2, 28, 15, 0)
        self.assertEqual(m.next(t2+1), expectedTimestamp_1)
        self.assertEqual(m.next(expectedTimestamp_1+1), expectedTimestamp_2)

        expectedTimestamp = getLocalizedTimestamp(2021, 3, 7, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, timezone=tzName)
        self.assertEqual(m.next(startTime+1), expectedTimestamp)

        expectedTimestamp = getLocalizedTimestamp(2021, 2, 26, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, 'Friday', 'Last', timezone=tzName)
        self.assertEqual(m.next(startTime+1), expectedTimestamp)

        expectedTimestamp = getLocalizedTimestamp(2021, 2, 21, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, 'Sunday', '3rd', timezone=tzName)
        self.assertEqual(m.next(startTime+1), expectedTimestamp)

        expectedTimestamp = getLocalizedTimestamp(2021, 2, 24, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, 'Wednesday', 'Last', timezone=tzName)
        self.assertEqual(m.next(startTime+1), expectedTimestamp)

        expectedTimestamp = getLocalizedTimestamp(2021, 3, 19, 15, 0)
        m.set(startTime, duration, m.MONTHLY, timezone=tzName)
        self.assertEqual(m.next(startTime + 1), expectedTimestamp)

        nowTimestamp = getLocalizedTimestamp(2021, 3, 1, 15, 0)
        expectedTimestamp = getLocalizedTimestamp(2021, 3, 8, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, 'Monday', '2nd', timezone=tzName)
        self.assertEqual(m.nextEvent(nowTimestamp), expectedTimestamp)

        nowTimestamp = getLocalizedTimestamp(2021, 3, 1, 15, 0)
        expectedTimestamp = getLocalizedTimestamp(2021, 3, 31, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, 'Wednesday', 'Last', timezone=tzName)
        self.assertEqual(m.nextEvent(nowTimestamp), expectedTimestamp)

        nowTimestamp = getLocalizedTimestamp(2022, 3, 8, 15, 0)
        expectedTimestamp = getLocalizedTimestamp(2022, 3, 14, 15, 0)
        m.set(startTime, duration, m.NTHWDAY, 'Monday', '2nd', timezone=tzName)
        self.assertEqual(m.nextEvent(nowTimestamp), expectedTimestamp)

        # skips
        m.skip = 2
        m.set(startTime, duration, m.DAILY, timezone=tzName)
        expectedTimestamp = getLocalizedTimestamp(2021, 2, 21, 15, 0)
        self.assertEqual(m.next(startTime + 1), expectedTimestamp)

    def testTimezonedWindowsWithDST(self):
        m = MaintenanceWindow('tester')
        m.dmd = self.dmd
        tzName = 'Europe/Kiev'
        tzInstance = tz.gettz(tzName)
        duration = 3*60

        def getLocalizedTimestamp(dateTime):
            localized_expected_time = dateTime.replace(tzinfo=tzInstance)
            return Time.awareDatetimeToTimestamp(localized_expected_time)

        FSOTM_Map = {
            # day before DST changing (Europe/Kiev) and first sunday of the month
            # Saturday      Sunday
            (2021, 3, 27):  datetime(2021, 4, 4),
            (2021, 10, 30): datetime(2021, 11, 7),
        }

        for (yy, mm, dd), sunday in FSOTM_Map.items():
            startTime = getLocalizedTimestamp(datetime(yy, mm, dd, 12, 0))
            nowTime = getLocalizedTimestamp(datetime(yy, mm, dd, 15, 0))

            m.set(startTime, duration, m.DAILY, timezone=tzName)
            expected_timestamp = getLocalizedTimestamp(datetime(yy, mm, dd, 12, 0) + relativedelta(days=1))
            self.assertEqual(m.nextEvent(nowTime), expected_timestamp)

            m.set(startTime, duration, m.WEEKLY, timezone=tzName)
            expected_timestamp = getLocalizedTimestamp(datetime(yy, mm, dd, 12, 0) + relativedelta(days=7))
            self.assertEqual(m.nextEvent(nowTime), expected_timestamp)

            m.set(startTime, duration, m.EVERY_WEEKDAY, timezone=tzName)
            expected_timestamp = getLocalizedTimestamp(datetime(yy, mm, dd, 12, 0) + relativedelta(days=2))
            self.assertEqual(m.nextEvent(nowTime), expected_timestamp)

            m.set(startTime, duration, m.NTHWDAY, 'Sunday', '1st', timezone=tzName)
            expected_timestamp = getLocalizedTimestamp(sunday + relativedelta(hours=12))
            self.assertEqual(m.nextEvent(nowTime), expected_timestamp)

            # DST: check that a mw takes the proper amount of time
            tt = getLocalizedTimestamp(datetime(yy, mm, dd, 0, 10, 9))
            m.set(tt, duration, m.DAILY, timezone=tzName)
            m.started = tt
            self.assertEqual(m.nextEvent(tt)-tt, duration*60-1)
            m.started = None


    def setupWindows(self, windowsDefs, maxWindows=10):
        """
        Setup windows from time t0 to time tmaxWindows-1

        Window defintions are a list of lists of the form
             [startTimeIndex, duration, startState]
        """
        class multiWindow:
            pass

        multiWin = multiWindow()

        # Create the test device
        multiWin.devid = 'unittestdevice1'
        multiWin.grpid = 'unittestGroup'
        multiWin.grp = self.dmd.Groups.createOrganizer(multiWin.grpid)
        # Note: A device's default creation state is state_Production
        multiWin.dev = self.dmd.Devices.createInstance(multiWin.devid)
        multiWin.dev.setGroups(multiWin.grp.id)

        multiWin.startDateTime = '1138531500'
        startDate_time = [ 2006, 1, 31, 10, 0, 12, 0, 0, 0 ]
        multiWin.tn = range(1,maxWindows)
        multiWin.time_tn = []
        multiWin.mwIds = []
        multiWin.mwObjs = []
        for time_point in multiWin.tn:
            startDate_time[3] = time_point
            multiWin.time_tn.append( mktime(startDate_time) )

            # Create a new window
            mwid = 'testNestedwindow%d' % time_point
            multiWin.mwIds.append(mwid)
            multiWin.grp.manage_addMaintenanceWindow(mwid)

            multiWin.mwObjs.append(
                  multiWin.grp.maintenanceWindows._getOb(mwid)
            )

        index = 0
        for startTimeIndex, duration, startState in windowsDefs:
            self.assert_( index < len(multiWin.mwObjs))
            #r = FakeRequest()
            r = None
            mw = multiWin.mwObjs[index]

            mw.manage_editMaintenanceWindow(
                startDateTime=multiWin.startDateTime,
                durationHours=str(duration),
                startProductionState=startState,
                REQUEST=r)
            #self.assertEquals(r.get('message', ''), 'Saved Changes')
            index += 1

        return multiWin


    def testSingleWindow(self):
        windowDefs = [
           [0, 2, state_Pre_Production],
           [3, 2, state_Test],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.getProductionState()

        # Begin first window
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)
        mws.mwObjs[0].end()
        self.assert_(mws.dev.getProductionState() == dev_orig_state)

        # Begin second window
        mws.mwObjs[1].begin(now=mws.time_tn[3])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[1].startProductionState)
        mws.mwObjs[1].end()
        self.assert_(mws.dev.getProductionState() == dev_orig_state)
    
    def testWindowWithFailedDevice(self):
        """
        Test maintenance window when one of the devices has a ConflictError. Changing production state 
        for the batch of devices shouldn't be failed if a single device has a ConflictError (ZEN-33274)
        """
        windowDefs = [
            [0, 3, state_Pre_Production],
        ]

        mws = self.setupWindows(windowDefs)
        numberOfDevices = 50

        def setProdStateMock(state, maintWindowChange=False, REQUEST=None):
            raise ConflictError()

        badDevice = self.dmd.Devices.createInstance("bad-device")
        badDevice.setProdState = setProdStateMock
        badDevice.setGroups(mws.grp.id)

        # We already have two devices in mws (the default one and the broken one).
        # There will be {numberOfDevices} devices in total
        for i in range(numberOfDevices-2):
            devid = "mwdev%d" % i
            dev = self.dmd.Devices.createInstance(devid)
            dev.setGroups(mws.grp.id)

        mws.mwObjs[0].begin(now=mws.time_tn[0], batchSize=10)
        changedDevices = [dev for dev in mws.grp.getDevices() 
                              if dev.getProductionState() == mws.mwObjs[0].startProductionState]
        
        # only one device is not changed, not the whole batch
        numberOfFailedDevices = numberOfDevices - len(changedDevices)
        self.assert_(numberOfFailedDevices == 1)

    def testNestedWindows(self):
        """
        Test nested windows from time t0 to time t4
        """
        windowDefs = [
           [0, 4, state_Pre_Production],
           [1, 2, state_Test],
        ]
        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.getProductionState()
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)

        # Begin nested window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.getProductionState() == min(mws.mwObjs[0].startProductionState,
                                                    mws.mwObjs[1].startProductionState))
        mws.mwObjs[1].end()
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)
        # End of nested window

        # Now end last maintenance window
        mws.mwObjs[0].end()

        self.assert_(mws.dev.getProductionState() == dev_orig_state)


    def testOverlappingWindows(self):
        """
        Look for issues with overlapping windows
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 5, state_Test],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.getProductionState()
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)

        # Begin nested window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.getProductionState() == min(mws.mwObjs[0].startProductionState,
                                                    mws.mwObjs[1].startProductionState))
        # End first window
        mws.mwObjs[0].end()
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[1].startProductionState)

        # Now end last maintenance window
        mws.mwObjs[1].end()

        self.assert_(mws.dev.getProductionState() == dev_orig_state)


    def testSameWindowEndTime(self):
        """
        Maintenance windows are processed by zenjobs in batch so the ordering
        of when two maintenance windows that end at the same time get processed
        are different. Since maintenance windows always return to the device's
        original state this should always succeed.
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 2, state_Test],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.getProductionState()

        # Begin first window
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)

        # Begin second window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[1].startProductionState)

        # Now end all maintenance windows
        mws.mwObjs[1].end()
        mws.mwObjs[0].end()

        self.assert_(mws.dev.getProductionState() == dev_orig_state)


    def testDeleteRunningWindow(self):
        """
        Deleting a running maintenance windows should return all existing devices
        to a sane state before allowing themselves to be closed.
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 5, state_Test],
        ]

        mws = self.setupWindows(windowDefs)
        dev_orig_state = mws.dev.getProductionState()

        # Begin first window
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)

        # Begin second window
        mws.mwObjs[1].begin(now=mws.time_tn[1])
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[1].startProductionState)

        # Now delete all maintenance windows
        #r = FakeRequest()
        r = None
        mws.grp.manage_deleteMaintenanceWindow(mws.mwIds[1], REQUEST=r)
        self.assert_(mws.dev.getProductionState() == mws.mwObjs[0].startProductionState)

        #r = FakeRequest()
        r = None
        mws.grp.manage_deleteMaintenanceWindow(mws.mwIds[0], REQUEST=r)
        self.assert_(mws.dev.getProductionState() == dev_orig_state)


    def ftestWindowStateChangeLoad(self):
        """
        The simple algorithm in use is O(n * m^2) for n devices and m windows,
        so we need to determine how bad "bad" really is in terms of running time.
        """
        windowDefs = [
           [0, 3, state_Pre_Production],
           [1, 5, state_Test],
        ]

        mws = self.setupWindows(windowDefs)
        print "Starting device creation"
        maxDevs = 2000
        for i in range(maxDevs):
           if i % 100 == 0:
               print i
           devid = "mwdev%d" % i
           dev = self.dmd.Devices.createInstance(devid)
           dev.setGroups(mws.grp.id)
        print "Finished device creation"

        # Test one window change
        now = time()
        mws.mwObjs[0].begin(now=mws.time_tn[0])
        finish = time()
        print "One maintenance window start for %d devices was %f seconds" % (
               maxDevs, finish - now)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMaintenanceWindows))
    return suite
