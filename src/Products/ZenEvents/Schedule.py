#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''Schedule

Walk through the maintenance schedule.

$Id$
'''

import time
import logging
from twisted.internet import reactor

from ZODB.transact import transact
from Products.ZenEvents.ZenEventClasses import Status_Update
from Products.ZenEvents import Event

class Schedule:

    def __init__(self, options, dmd):
        "start executing the schedule"
        self.dmd = dmd
        self.maintenance = []
        self.options = options
        self.log = logging.getLogger("zen.Schedule")
        self.workList = []
        self.timer = None


    def buildOptions(self, parser):
        "Set options in a borrowed parser"


    def start(self):
        "Start working the schedule"
        self.configCycle()


    def configCycle(self):
        "Basic event-driven config loop"
        try:
            self.run()
        except Exception:
            self.log.exception("Error processing maintenance windows - will try again in % seconds", self.options.maintenceWindowCycletime)
        reactor.callLater(self.options.maintenceWindowCycletime, self.configCycle)


    def sync(self):
        "Synch with the database"
        self.dmd._p_jar.sync()

    def getWindows(self):
        result = []
        catalog = getattr(self.dmd, 'maintenanceWindowSearch', None)
        if catalog is not None:
            for brain in catalog():
                try:
                    ob = brain.getObject()
                except KeyError:
                    # We're just catching the symptom for now, but an actual
                    # fix will be forthcoming.
                    # http://dev.zenoss.org/trac/ticket/3105
                    pass
                else:
                    result.append(ob)
        else: # Should be removed in 2.3.
            self.log.warn('Run zenmigrate to index your maintenance windows.')
            for dev in self.dmd.Devices.getSubDevices():
                result.extend(dev.maintenanceWindows())
            for name in 'Systems', 'Locations', 'Groups', 'Devices':
                organizer = getattr(self.dmd, name)
                for c in organizer.getSubOrganizers():
                    result.extend(c.maintenanceWindows())
                result.extend(organizer.maintenanceWindows())
            for lst in [self.dmd.ZenUsers.getAllUserSettings(),
                        self.dmd.ZenUsers.getAllGroupSettings()]:
                for us in lst:
                    for ar in us.objectValues(spec="ActionRule"):
                        result.extend(w for w in ar.windows() if w.enabled)
        return result

    def run(self):
        "Re-read work list from the database"
        self.sync()
        self.workList = self.getWindows()
        self.runEvents()


    @transact
    def makeWorkList(self, now, workList):
        """
        Returns the list of tuples where 0 is the next time the
        window should run and the 1 index is the window itself.
        If there is no next run and the window has started this
        method ends the windows.

        This method is wrapped in a transact block because there
        is the chance that we could set the production state on
        devices if the "end" method is called.
        """
        work = [(mw.nextEvent(now), mw) for mw in workList]
        work.sort()
        # note that None is less than any number of seconds
        while len(work):
            t, mw = work[0]
            if t: break
            if mw.enabled:
                self.log.debug("Never going to run Maintenance "
                               "Window %s for %s again",
                               mw.getId(), mw.target().getId())
            if mw.started:
                mw.end()
            work.pop(0)
        return work

    def now(self):
        return time.time()

    def runEvents(self):
        "Execute all the maintanance windows at the proper time"
        if self.timer and not self.timer.called:
            self.timer.cancel()
            self.timer = None

        # sort events by the next occurance of something to do
        now = self.now()
        work = self.makeWorkList(now, self.workList)
        self.workList = [mw for t, mw in work]
        # fire events that should be done now
        for next, mw in work:
            if next <= now:
                how = {True:'stopping', False:'starting'}[bool(mw.started)]
                severity = {True:Event.Clear, False:Event.Info}[bool(mw.started)]
                # Note: since the MWs always return devices back to their original
                #       prod state, and there may be many devices, just provide an
                #       'unknown' production state for stopping
                prodState = {True:-99, False:mw.startProductionState}[bool(mw.started)]
                mwId = mw.getId()
                devices = mw.target().getId()
                msg = "Maintenance window %s %s for %s" % (how, mwId, devices)
                self.log.debug(msg)
                dedupid = '|'.join(["zenjobs",self.monitor,mwId,devices])
                self.sendEvent(Event.Event(
                    component="zenjobs",
                    severity=severity,
                    dedupid=dedupid,
                    eventClass=Status_Update,
                    eventClassKey="mw_change",
                    summary=msg,
                    eventKey='|'.join([mwId,devices]),
                    maintenance_window=mwId,
                    maintenance_devices=devices,
                    device=self.monitor,
                    prodState=prodState,
                    monitor=self.monitor,
                    status="New"
                ))
                mw.execute(next,
                           batchSize=self.options.maintenceWindowBatchSize,
                           inTransaction=True)
            else:
                break

        work = self.makeWorkList(now, self.workList)
        if work:
            wait = max(0, work[0][0] - now)
            self.log.debug("Waiting %f seconds", wait)
            self.timer = self.callLater(wait)

    def callLater(self, seconds):
        return reactor.callLater(seconds, self.runEvents)


if __name__ == "__main__":
    class MySchedule(Schedule):
        currentTime = time.time()
        objs = None
        def now(self):
            return self.currentTime
        def callLater(self, seconds):
            self.currentTime += seconds
        def executeMaintenanceWindow(self, mw, timestamp):
            print 'executing', mw.id, time.ctime(timestamp)
            mw.execute(timestamp)
        def getWindows(self):
            if self.workList:
                return self.workList
            return Schedule.getWindows(self)
        def commit(self):
            pass
        sync = commit

    from Products.ZenUtils.ZCmdBase import ZCmdBase

    cmd = ZCmdBase()
    class Options: pass
    s = MySchedule(Options(), cmd.dmd)
    # compute the schedule for 30 days
    end = s.currentTime + 60*60*24*30
    while s.currentTime < end:
        s.run()
