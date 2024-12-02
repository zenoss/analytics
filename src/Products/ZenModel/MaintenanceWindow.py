##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, 2014, 2021 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """MaintenanceWindow

A scheduled period of time during which a window is under maintenance.

"""

DAY_SECONDS = 24*60*60
WEEK_SECONDS = 7*DAY_SECONDS

import re
import time
import dateutil.tz as tz
import calendar
import logging
log = logging.getLogger("zen.MaintenanceWindows")


from datetime import datetime
from dateutil.relativedelta import relativedelta

from AccessControl import ClassSecurityInfo
from zope.interface import implements
from ZenossSecurity import *
from ZenModelRM import ZenModelRM
from Products.ZenModel.interfaces import IIndexed
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

from zope.event import notify
from Products.Zuul.catalog.events import IndexingEvent

import transaction
from ZODB.transact import transact
from ZODB.POSException import ConflictError, POSKeyError, ReadConflictError


def addMonth(secs, dayOfMonthHint=0, tzInstance=tz.tzutc()):
    dateTime = datetime.fromtimestamp(secs, tzInstance)
    newYear = dateTime.year
    newMonth = dateTime.month + 1

    if newMonth > 12:
        newYear += 1
        newMonth = 1

    lastDayOfMonth = calendar.monthrange(newYear, newMonth)[1]
    newDay = min(dayOfMonthHint, lastDayOfMonth)
    newDateTime = datetime(
        year=newYear, 
        month=newMonth, 
        day=newDay, 
        hour=dateTime.hour, 
        minute=dateTime.minute, 
        second=dateTime.second,
        tzinfo=tzInstance
    )

    return Time.awareDatetimeToTimestamp(newDateTime)

RETURN_TO_ORIG_PROD_STATE = -99

class MaintenanceWindow(ZenModelRM):

    implements(IIndexed)
    meta_type = 'MaintenanceWindow'

    default_catalog = 'maintenanceWindowSearch'

    name = None
    start = None
    started = None
    duration = 60
    repeat = 'Never'
    days = 'Sunday'
    occurrence = '1st'
    startProductionState = 300
    stopProductionState = RETURN_TO_ORIG_PROD_STATE
    enabled = True
    skip = 1
    timezone = 'UTC'
    tzInstance = tz.tzutc()

    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'start', 'type':'int', 'mode':'w'},
        {'id':'started', 'type':'int', 'mode':'w'},
        {'id':'duration', 'type':'int', 'mode':'w'},
        {'id':'repeat', 'type':'string', 'mode':'w'},
        {'id':'days', 'type':'string', 'mode':'w'},
        {'id':'occurrence', 'type':'string', 'mode':'w'},
        {'id':'skip', 'type':'int', 'mode':'w'},
        {'id': 'timezone', 'type':'string', 'mode':'w'},
        )

    factory_type_information = (
        {
            'immediate_view' : 'maintenanceWindowDetail',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'maintenanceWindowDetail'
                , 'permissions'   : (ZEN_MAINTENANCE_WINDOW_VIEW, )
                },
            )
         },
        )

    backCrumb = 'deviceManagement'
    _relations = (
        ("productionState", ToOne(ToManyCont, "Products.ZenModel.MaintenanceWindowable", "maintenanceWindows")),
        )

    security = ClassSecurityInfo()

    REPEAT = "Never/Daily/Every Weekday/Weekly/Monthly: day of month/Monthly: day of week".split('/')
    NEVER, DAILY, EVERY_WEEKDAY, WEEKLY, MONTHLY, NTHWDAY = REPEAT
    DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    OCCURRENCE = ['1st', '2nd', '3rd', '4th', '5th', 'Last']
    def __init__(self, id):
        ZenModelRM.__init__(self, id)
        self.start = time.time()
        self.enabled = False

    def set(self, start, duration, repeat, days='Sunday', occurrence='1st', enabled=True, timezone='UTC'):
        self.start = start
        self.duration = duration
        self.repeat = repeat
        self.enabled = enabled
        self.days = days
        self.occurrence = occurrence
        self.timezone = timezone
        self.tzInstance = tz.gettz(timezone)

    def displayName(self):
        if self.name is not None: return self.name
        else: return self.id

    def repeatOptions(self):
        "Provide the list of REPEAT options"
        return self.REPEAT

    def daysOptions(self):
        "Provide the list of DAYS options"
        return self.DAYS

    def occurrenceOptions(self):
        "Provide the list of OCCURRENCE options"
        return self.OCCURRENCE

    def getTargetId(self):
        return self.target().id

    # Nice methods used by the GUI for presentation purposes
    def niceDuration(self):
        """Return a human readable version of the duration in
        days, hours, minutes"""
        return Time.Duration(self.duration*60)

    def niceStartDate(self):
        "Return a date in the format use by the calendar javascript"
        return Time.USDate(self.start)

    def niceStartDateTime(self):
        "Return start time as a string with nice sort qualities"
        return "%s %s" % (datetime.fromtimestamp(self.start, self.tzInstance).strftime("%Y/%m/%d %H:%M:%S"), self.timezone)

    def niceStartProductionState(self):
        "Return a string version of the startProductionState"
        return self.dmd.convertProdState(self.startProductionState)

    def niceStopProductionState(self):
        "Return a string version of the stopProductionState"
        return 'Original'

    def niceStartHour(self):
        return datetime.fromtimestamp(self.start, self.tzInstance).hour

    def niceStartMinute(self):
        return datetime.fromtimestamp(self.start, self.tzInstance).minute

    def niceRepeat(self):
        if self.repeat == self.REPEAT[-1]:
            return self.occurrence + ' ' + self.days + ' of the month'
        return self.repeat

    @staticmethod
    def durationStringParser(duration_string):
        parsed_duration = {}
        if 'days' not in duration_string:
            hours_minutes_seconds = duration_string.split(':')
            if len(hours_minutes_seconds) == 3:
                parsed_duration.update({
                    'hours': str(hours_minutes_seconds[0]),
                    'minutes': str(hours_minutes_seconds[1]),
                    'seconds': str(hours_minutes_seconds[2])
                })
            elif len(hours_minutes_seconds) == 2:
                parsed_duration.update({
                    'minutes': str(hours_minutes_seconds[0]),
                    'seconds': str(hours_minutes_seconds[1])
                })
            elif len(hours_minutes_seconds) == 1:
                parsed_duration.update({
                    'seconds': str(hours_minutes_seconds[0])
                })
        else:
            days_hours_minutes = duration_string.split(' days ')
            hours_minutes_seconds = days_hours_minutes[1].split(':')
            parsed_duration.update({
                'days': str(days_hours_minutes[0]),
                'hours': str(hours_minutes_seconds[0]),
                'minutes': str(hours_minutes_seconds[1]),
                'seconds': str(hours_minutes_seconds[2])
            })
        return parsed_duration

    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT,
                              'manage_editMaintenanceWindow')
    def manage_editMaintenanceWindow(self,
                                     startDate='',
                                     startHours='00',
                                     startMinutes='00',
                                     durationDays='0',
                                     durationHours='00',
                                     durationMinutes='00',
                                     repeat='Never',
                                     days='Sunday',
                                     occurrence='1st',
                                     startProductionState=300,
                                     stopProductionState=RETURN_TO_ORIG_PROD_STATE,
                                     enabled=True,
                                     skip=1,
                                     REQUEST=None,
                                     startDateTime=None,
                                     timezone=None):
        "Update the maintenance window from GUI elements"
        def makeInt(v, fieldName, minv=None, maxv=None, acceptBlanks=True):
            if acceptBlanks:
                if isinstance(v, str):
                    v = v.strip()
                v = v or '0'
            try:
                v = int(v)
                if minv is not None and v < minv:
                    raise ValueError
                if maxv is not None and v > maxv:
                    raise ValueError
            except ValueError:
                if minv is None and maxv is None:
                    msg = '%s must be an integer.' % fieldName
                elif minv is not None and maxv is not None:
                    msg = '%s must be between %s and %s inclusive.' % (
                                fieldName, minv, maxv)
                elif minv is not None:
                    msg = '%s must be at least %s' % (fieldName, minv)
                else:
                    msg = '%s must be no greater than %s' % (fieldName, maxv)
                msgs.append(msg)
                v = None
            return v

        oldAuditData = self.getAuditData()
        prodStates = dict((key, value) for (key,value) in self.dmd.getProdStateConversions())
        msgs = []
        self.enabled = bool(enabled)

        if not timezone:
            # Use container timezone
            timezone = time.strftime('%Z')
        try:
            tzInstance = tz.gettz(timezone)
        except Exception:
            msgs.append("'timezone' has wrong value")
    
        if startDateTime:
            t = int(startDateTime)
        else:
            startHours = int(startHours) if startHours else 0
            startMinutes = int(startMinutes) if startMinutes else 0
            self.enabled = bool(enabled)
            try:
                month, day, year = re.split('[^ 0-9]', startDate)
            except ValueError:
                msgs.append("Date needs three number fields")
            day = int(day)
            month = int(month)
            year = int(year)
            if not msgs:
                startDateTime = datetime(year, month, day, startHours, startMinutes, tzinfo=tzInstance)
                t = Time.awareDatetimeToTimestamp(startDateTime)
        if repeat not in self.REPEAT:
            msgs.append('\'repeat\' has wrong value.')
        if not isinstance(enabled, bool):
            msgs.append('\'enabled\' has wrong value, use true or false.')
        if not (startProductionState in prodStates.values() or
            prodStates.get(startProductionState, None)):
            msgs.append('\'startProductionState\' has wrong value.')
        elif isinstance(startProductionState, str):
            startProductionState = prodStates[startProductionState]
        if not msgs:
            durationDays = makeInt(durationDays, 'Duration days',
                                        minv=0)
            durationHours = makeInt(durationHours, 'Duration hours',
                                        minv=0, maxv=23)
            durationMinutes = makeInt(durationMinutes, 'Duration minutes',
                                        minv=0, maxv=59)
        if not msgs:
            duration = (durationDays * (60*24) +
                        durationHours * 60 +
                        durationMinutes)

            if duration < 1:
                msgs.append('Duration must be at least 1 minute.')
        if msgs:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Window Edit Failed',
                    '\n'.join(msgs),
                    messaging.WARNING
                )
            else:
                raise Exception('Window Edit Failed: ' + '\n'.join(msgs))
        else:
            self.start = t
            self.duration = duration
            self.repeat = repeat
            self.days = days
            self.occurrence = occurrence
            self.startProductionState = startProductionState
            self.stopProductionState = stopProductionState
            self.skip = skip
            self.timezone = timezone
            self.tzInstance = tzInstance
            now = time.time()
            if self.started:
                if ((t + duration * 60) < now) or (t > now) or (not self.enabled):
                    # We're running. If we should have already ended OR the start was
                    # moved into the future OR the MW is now disabled, end().
                    self.end()
            elif (t < now) and ((t + duration * 60) > now) and (self.enabled):
                # We aren't running, but we've scheduled the MW to be going on right now.
                self.begin()

            if REQUEST:
                flare = 'Maintenance window changes were saved.'
                if self.enabled:
                    flare += ' Next run on %s' % time.strftime(
                        "%m/%d/%Y %H:%M:%S", time.localtime(self.next()))
                messaging.IMessageSender(self).sendToBrowser(
                    'Window Updated',
                    flare
                )
                audit('UI.MaintenanceWindow.Edit', self,
                      data_=self.getAuditData(),
                      oldData_=oldAuditData)
        if REQUEST:
            return REQUEST.RESPONSE.redirect(self.getUrlForUserCommands())


    def nextEvent(self, now):
        "Return the time of the next begin() or end()"
        if self.started:
            return self.started + self.duration * 60 - 1
        # ok, so maybe "now" is a little late: start anything that
        # should have been started by now
        return self.next(now - self.duration * 60 + 1)


    security.declareProtected(ZEN_VIEW, 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        "fix up breadCrumbs to add a link back to the Manage tab"
        bc = super(MaintenanceWindow, self).breadCrumbs(terminator)
        url, display = bc[-2]
        url += "/" + self.backCrumb
        bc.insert(-1, (url, 'manage'))
        return bc


    def occurDay(self, start, now, skip=1, day=6, occur=0):
        startDateTime = datetime.fromtimestamp(start, self.tzInstance)
        timeDelta = relativedelta(hours=startDateTime.hour, minutes=startDateTime.minute, seconds=startDateTime.second)
        log.debug('start date: %s; day: %d; occur: %d; skip: %d', str(startDateTime), day,
                  occur, skip)
        # get a list of (mday, wday) tuples for current month
        c = calendar.Calendar(firstweekday=0)
        flatter = sum(c.monthdays2calendar(startDateTime.year, startDateTime.month), [])
        if occur == 5:
            flatter = reversed(flatter)
            tmp_occur = 0
        else:
            tmp_occur = occur
        count = 0
        #find Nth occurrence of week day
        for mday, wday in flatter:
            if wday == day and mday > 0:
                count += 1
                log.debug('found wday %d, mday %d, count %d', wday, mday, count)
                if count == tmp_occur + 1 and mday >= startDateTime.day:
                    log.debug('count matched, mday %d', mday)
                    startDateTime = datetime(startDateTime.year, startDateTime.month, mday, tzinfo=self.tzInstance) + timeDelta
                    startTimestamp = Time.awareDatetimeToTimestamp(startDateTime)
                    # do we need to skip this day?
                    if skip > 1:
                        log.debug('skipping this occurrence. skip = %d', skip)
                        return self.occurDay(startTimestamp + DAY_SECONDS, now, skip - 1,
                                             day, tmp_occur)
                    elif startTimestamp >= now:
                        log.debug('Window will start on: %s',
                                  str(datetime.fromtimestamp(startTimestamp, self.tzInstance)))
                        return startTimestamp
        
        # couldn't find start day in current month, switching to 1st day of the next month
        if startDateTime.month == 12:
            startDateTime = datetime(startDateTime.year + 1, 1, 1, tzinfo=self.tzInstance)
        else:
            startDateTime = datetime(startDateTime.year, startDateTime.month + 1, 1, tzinfo=self.tzInstance)
        startDateTime += timeDelta

        return self.occurDay(Time.awareDatetimeToTimestamp(startDateTime), now, skip, day, occur)


    def next(self, now=None):
        """
        From Unix time_t now value, return next time_t value
        for the window to start, or None
        This adjusts for DST changes.
        """
        return self._next(now)


    def _next(self, now):
        if not self.enabled:
            return None

        if self.skip is None:
            self.skip = 1

        if now is None:
            now = time.time()

        if now < self.start:
            return self.start
        
        nowDateTime = datetime.fromtimestamp(now, self.tzInstance)
        startDateTime = datetime.fromtimestamp(self.start, self.tzInstance)
        diffBetweenNowAndStart = nowDateTime - startDateTime

        if self.repeat == self.NEVER:
            if now > self.start:
                return None
            return self.start

        elif self.repeat == self.DAILY:   
            daysSince = diffBetweenNowAndStart.days
            dateTime = datetime.fromtimestamp(self.start, self.tzInstance) + relativedelta(days=daysSince + self.skip)
            return Time.awareDatetimeToTimestamp(dateTime)

        elif self.repeat == self.EVERY_WEEKDAY:
            weeksSince = diffBetweenNowAndStart.days // 7
            weekdaysSince = weeksSince * 5
            # start at the most recent week-even point from the start
            baseDateTime = datetime.fromtimestamp(self.start, self.tzInstance) + relativedelta(weeks=weeksSince)
            while 1:
                dow = baseDateTime.weekday()
                if dow not in (5,6):
                    if baseDateTime > nowDateTime and weekdaysSince % self.skip == 0:
                        break
                    weekdaysSince += 1
                baseDateTime += relativedelta(days=1)
            assert baseDateTime >= nowDateTime
            return Time.awareDatetimeToTimestamp(baseDateTime)

        elif self.repeat == self.WEEKLY:
            weeksSince = diffBetweenNowAndStart.days // 7
            dateTime = datetime.fromtimestamp(self.start, self.tzInstance) + relativedelta(weeks=weeksSince + self.skip)
            return Time.awareDatetimeToTimestamp(dateTime)

        elif self.repeat == self.MONTHLY:
            months = 0
            m = self.start
            dayOfMonthHint = datetime.fromtimestamp(self.start, self.tzInstance).day
            while m < now or months % self.skip:
                m = addMonth(m, dayOfMonthHint, self.tzInstance)
                months += 1
            return m

        elif self.repeat == self.NTHWDAY:
            return self.occurDay(
                                 self.start,
                                 now,
                                 self.skip,
                                 self.DAYS.index(self.days),
                                 self.OCCURRENCE.index(self.occurrence))
        raise ValueError('bad value for MaintenanceWindow repeat: %r' %self.repeat)

    def target(self):
        return self.productionState().primaryAq()

    def isActive(self):
        """
        Return whether or not the maintenance window is active.

        @return: is this window active or not?
        @rtype: boolean
        """
        if not self.enabled or self.started is None:
            return False
        return True

    def fetchDeviceMinProdStates(self, devices=None):
        """
        Return a dictionary of devices and their minimum production state from
        all maintenance windows.

        Note: This method should be moved to the zenjobs command in order to
              improve performance.

        @return: dictionary of device_id:production_state
        @rtype: dictionary
        """
        # Get all maintenance windows + action rules from all device classes,
        # devices, Systems, Locations, and Groups.
        # Yes, it's O(m * n)
        minDevProdStates = {}
        cat = getattr(self, self.default_catalog)
        for entry in cat():
            try:
                mw = entry.getObject()
            except Exception:
                continue

            if not mw.isActive():
                # Note: if the mw has just ended, the self.end() method
                #       has already made the mw inactive before this point
                continue

            log.debug("Updating min MW Prod state using state %s from window %s",
                    mw.startProductionState, mw.displayName())

            if self.primaryAq() == mw.primaryAq():
                # Special case: our window's devices
                mwDevices = devices
            else:
                mwDevices = mw.fetchDevices()

            for device in mwDevices:
                guid = IGlobalIdentifier(device).getGUID()
                state = minDevProdStates.get(guid, None)
                if state is None or state > mw.startProductionState:
                    minDevProdStates[guid] = mw.startProductionState
                    log.debug("MW %s has lowered %s's min MW prod state to %s",
                        mw.displayName(), device.id, mw.startProductionState)

        return minDevProdStates


    def fetchDevices(self):
        """
        Get the list of devices from our maintenance window.
        """
        target = self.target()
        from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
        from Products.ZenModel.ComponentOrganizer import ComponentOrganizer
        if isinstance(target, DeviceOrganizer):
            devices = target.getSubDevices()
        elif isinstance(target, ComponentOrganizer):
            devices = target.getSubComponents()
        else:
            devices = [target]

        return devices


    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT, 'setProdState')
    def setProdState(self, state, ending=False, batchSize=None,
                     inTransaction=False):
        """
        At any one time there is one production state for each device to be in,
        and that is the state that is the most 'blacked out' in all of the active
        maintenance windows affecting that device.  When the last maintenance
        window affecting a device has ended, the original production state of the
        device is used to determine the end state of the device.

        Maintenance windows are processed by zenjobs in batch so the ordering
        of when two maintenance windows that end at the same time get processed
        is non-deterministic.  Since there is only one stop production state now,
        this is not an issue.

        @parameter state: hint from the maint window about device's start or stop state
        @type state: integer
        @parameter ending: are we ending a maintenance window?
        @type ending: boolean
        @parameter batchSize: number of processed devices per separate transaction
        @type batchSize: integer
        @parameter inTransaction: process each batch in separate transaction
        @type inTransaction: boolean
        """
        # Note: self.begin() starts our window before we get called, so the
        #       following takes into account our window state too.
        #       Conversely, self.end() ends the window before calling this code.
        devices = self.fetchDevices()
        unchangedDevices = []
        minDevProdStates = self.fetchDeviceMinProdStates(devices)

        def _setProdState(devices_batch):
            for device in devices_batch:
                guid = IGlobalIdentifier(device).getGUID()
                # In case we try to move Component Group into MW
                # some of objects in CG may not have production state
                # we skip them.
                if ending:
                    # Note: If no maintenance windows apply to a device, then the
                    #       device won't exist in minDevProdStates
                    # This takes care of the case where there are still active
                    # maintenance windows.
                    minProdState = minDevProdStates.get(guid,
                                                device.getPreMWProductionState())

                elif guid in minDevProdStates:
                    minProdState = minDevProdStates[guid]

                else: # This is impossible for us to ever get here as minDevProdStates
                      # has been added by self.fetchDeviceMinProdStates()
                    log.error("The device %s does not appear in any maintenance"
                              " windows (including %s -- which is just starting).",
                              device.id, self.displayName())
                    continue

                # ZEN-13197: skip decommissioned devices
                if device.getPreMWProductionState() and device.getPreMWProductionState() < 300:
                    continue

                self._p_changed = 1
                # Changes the current state for a device, but *not*
                # the preMWProductionState
                oldProductionState = self.dmd.convertProdState(device.getProductionState())
                # When MW ends Components will acquire production state from device
                if not minProdState:
                    newProductionState = "Acquired from parent"
                else:
                    newProductionState = self.dmd.convertProdState(minProdState)
                log.info("MW %s changes %s's production state from %s to %s",
                         self.displayName(), device.id, oldProductionState,
                         newProductionState)
                audit('System.Device.Edit', device, starting=str(not ending),
                    maintenanceWindow=self.displayName(),
                    productionState=newProductionState,
                    oldData_={'productionState':oldProductionState})
                if minProdState is None:
                    device.resetProductionState()
                else:
                    device.setProdState(minProdState, maintWindowChange=True)

        def retrySingleDevices(devices_batch):
            log.warn("Retrying devices individually")
            for dev in devices_batch:
                try:
                    processFunc([dev])
                except Exception:
                    log.exception(
                        "The production stage change for %s raised the exception.", dev
                    )
                    unchangedDevices.append(dev)

        def processBatchOfDevices(devices, batchSize):
            for i in xrange(0, len(devices), batchSize):
                log.info('MW %s processing batch #%s', self.displayName(), i / batchSize + 1)
                dev_chunk = devices[i:i + batchSize]
                try:
                    processFunc(dev_chunk)
                except (ConflictError, POSKeyError, ReadConflictError) as e:
                    log.warn(
                        "While processing batch of %d devices exception was raised. %s",
                        len(dev_chunk), e
                    )
                    retrySingleDevices(dev_chunk)
                except Exception:
                    # We're expecting ConflictError, POSKeyError, ReadConflictError, and handle them with retries
                    # production state change. All other exceptions are an unexplored area that should be properly
                    # processed in the future instead of the stub below.
                    log.exception("Unexpected Exception encountered")
                    retrySingleDevices(dev_chunk)

        if inTransaction:
            processFunc = transact(_setProdState)
            # Commit transaction as errors during batch processing may
            # abort transaction and changes to the object will not be saved.
            transaction.commit()
        else:
            processFunc = _setProdState

        # Adding exception handling for the following:
        # ConflictError, POSKeyError and ReadConflictError.
        #
        # If any of the listed exceptions are encountered, we will retry
        # devices in the batch individually.  If batchSize isn't
        # specified and we encounter one of these exceptions, we will
        # then specify a batch size and retry the devices in batches.
        # If there are exceptions in these batches, we will retry the
        # devices individually.  This will ensure that maintenance
        # windows as a whole do not fail due to these exceptions.
        # Fixes ZEN-31805.
        if batchSize:
            processBatchOfDevices(devices, batchSize)
        else:
            try:
                processFunc(devices)
            except (ConflictError, POSKeyError, ReadConflictError) as e:
                log.warn(
                    "Exception encountered and no batchSize specified. "
                    "%s. Retrying in batches.",
                    e
                )
                processBatchOfDevices(devices, 10)
            except Exception:
                log.exception("Unexpected Exception encountered")
                processBatchOfDevices(devices, 10)

        if unchangedDevices:
            log.error(
                "Unable to change Production State on: %s", unchangedDevices
            )

    def begin(self, now=None, batchSize=None, inTransaction=False):
        """
        Hook for entering the Maintenance Window: call if you override
        """
        log.info("Maintenance window %s starting", self.displayName())
        if not now:
            now = time.time()

        # Make sure that we've started before the calculation of the production
        # state occurs.
        self.started = now
        self.setProdState(self.startProductionState, batchSize=batchSize,
                          inTransaction=inTransaction)
        log.info("Finished start of maintenance window %s", self.displayName())


    def end(self, batchSize=None, inTransaction=False):
        """
        Hook for leaving the Maintenance Window: call if you override
        """
        log.info("Maintenance window %s ending", self.displayName())
        # Make sure that the window has ended before the calculation of
        # the production state occurs.
        self.started = None
        self.setProdState(self.stopProductionState, ending=True,
                          batchSize=batchSize, inTransaction=inTransaction)
        log.info("Finished end of maintenance window %s", self.displayName())


    def execute(self, now=None, batchSize=None, inTransaction=False):
        "Take the next step: either start or stop the Maintenance Window"
        if self.started:
            self.end(batchSize, inTransaction)
        else:
            self.begin(now, batchSize, inTransaction)


    def getAuditData(self):
        return {
            'enabled': str(self.enabled),
            'startDate': self.niceStartDate(),
            'startTime': '%02d:%02d' % (self.niceStartHour(), self.niceStartMinute()),
            'duration': self.niceDuration(),
            'repeat': self.repeat,
            'productionState': self.niceStartProductionState(),
        }


DeviceMaintenanceWindow = MaintenanceWindow
OrganizerMaintenanceWindow = MaintenanceWindow


from Products.ZCatalog.ZCatalog import manage_addZCatalog
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex, makePathIndex
from Products.CMFCore.utils import getToolByName


def createMaintenanceWindowCatalog(dmd):

    catalog_name = 'maintenanceWindowSearch'

    manage_addZCatalog(dmd, catalog_name, catalog_name)
    cat = getToolByName(dmd, catalog_name)

    id_index = makeCaseInsensitiveFieldIndex('getId')
    cat._catalog.addIndex('id', id_index)
    cat.addColumn('id')
    cat._catalog.addIndex('getPhysicalPath', makePathIndex('getPhysicalPath'))
    cat.addColumn('getPhysicalPath')

