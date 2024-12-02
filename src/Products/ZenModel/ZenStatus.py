##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from __future__ import division

__doc__="""ZenStatus

Track status information about some monitored object.
if status = -1 the object has not been tested
if status = -2 the object has failed a DNS lookup
if status = 0 the object has passed its test
if status > 0 the object has failed its test status times

This class should track availability as well!!!

$Id: ZenStatus.py,v 1.28 2004/05/11 22:59:23 edahl Exp $"""

import calendar

from Persistence import Persistent
from DateTime import DateTime

defaultColor = "#d02090"

class ZenStatus(Persistent):

    conversions = { 
        -2 : "No DNS",
        -1 : "Not Tested",
         0 : "Up",
    }

    def __init__(self, status=-1):
        self.status = status

    def getStatus(self):
        """get objects current status this is the number of failure
        increments that have been called"""
        return self.status
 

    def getStatusString(self):
        """get status as a string will convert as per converstions"""
        return (self.conversions[self.status]
                    if self.status in self.conversions else self.status)


    def setStatus(self, status):
        self.status = int(status)

    def incr(self):
        """increment the failure status"""
        self.status += 1

    def reset(self):
        """reset status when failure is over"""
        self.status = 0

    def color(self):
        """get the color to display in the gui"""
        retval = defaultColor
        if self.status == 0:
            retval="#00ff00"
        elif self.status == -2:
            retval = "#ff9900"
        elif self.status > 0:
            retval = "#ff0000"
        return retval


class ZenAvailability(ZenStatus):

    def __init__(self, status=-1):
        ZenStatus.__init__(self, status)
        self.failstart = 0  # start of current failure as DateTime
        self.failincr = 0    # DateTime of last failure increment call
        self.todaydown = 0  # total downtime today in seconds
        self.yearlydata = {DateTime().year() : YearlyDownTime()}


    def incr(self):
        """increment the failure time of a monitored object
        if we are in a new day since last failure move old 
        day data to yearly data and reset for todays availability
        this must be called once a day to work correctly!!!"""
        if self.failstart == 0: 
            self.failstart = self.failincr = DateTime()
        if self.status < 0: self.status = 1
        delta = long((DateTime() - self.failincr) * 86400)
        if not self.failincr.isCurrentDay():
            yavail = self._getYearlyData(self.failstart.year())
            now = DateTime()
            newdaydown = long((now.earliestTime() - now) * 86400)
            yesterdaydown = self.todaydown + (delta - newdaydown)
            yavail.addDaily(yesterdaydown)
            self.todaydown = 0
            delta = newdaydown
        self.todaydown += delta
        self.status += delta
        self.failincr = DateTime()
    

    def reset(self):
        """reset the objects failure status"""
        self.status = 0
        self.failstart = 0
        self.failincr = 0

    
    def getStatusString(self):
        """current down time in days hours or seconds"""
        status = self.getStatus()
        if status in self.conversions:
            return self.conversions[status]
        dt = DateTime() - self.failstart
        days = int(dt)
        hours = int(dt * 24) % 24
        mins = int(dt * 24*60) % 60
        secs = round(dt * 86400) % 60
        return "%dd:%02dh:%02dm:%02ds" % (days, hours, mins, secs)


    def getStatus(self):
        """get current down time in seconds"""
        if self.status < 0: return self.status
        if self.failstart == 0: return 0
        return int(round((DateTime() - self.failstart) * 86400))
        

    def getAvailPercent(self, start, end=None):
        """get availability for a date range as a float between 100.0 and 0.0"""
        if self.status < 0: return -1
        if not end: end = DateTime()
        delta = long((end - start) * 86400.0)
        dt = self.getDownTime(start,end)
        if dt < 0: return dt
        return 100.0 - ((self.getDownTime(start, end) / delta)*100)


    def getAvailPercentString(self, start, end=None):
        """get availability for a date range as a string for display"""
        avail = self.getAvailPercent(start, end)
        if avail < 0: return "Unknown"
        return "%.3f%%" % self.getAvailPercent(start, end)


    def getAvail30(self):
        """get the 30 day rolling availability of this object"""
        return self.getAvailPercent(DateTime()-30)


    def getAvail30String(self):
        """get the 30 day rolling availability of this object"""
        return self.getAvailPercentString(DateTime()-30)


    def getDownTime(self, start, end=None):
        """calculate the down time in seconds using start and end DateTime
        if no end is passed the current time is assumed"""
        if not end: end = DateTime()
        syear = start.year()
        eyear = end.year()
        dt = -1 
        if syear == eyear:
            dt = self._getDownTime(syear, start, end)
        else: 
            dt = self._getDownTime(syear, start=start)
            for y in range(syear+1, eyear):
                dt += self._getDownTime(y)
            dt += self._getDownTime(eyear, end=end)
        if end.isCurrentDay(): dt += self.todaydown
        return dt
      

    def _getDownTime(self, year, start=None, end=None):
        """check to see if we have year data for year and return it"""
        dt = -1
        dt = self._getYearlyData(year).getDownTime(start, end)
        return dt


    def _getYearlyData(self, year):
        """get or create a YearlyDownTime object"""
        if not year in self.yearlydata:
            self.yearlydata[year] = YearlyDownTime()
        return self.yearlydata[year]

            
class YearlyDownTime(Persistent):
    """this would take less space as a dict with but it would take longer
    to query not sure which is better going with faster and bigger :)"""

    def __init__(self):
        days = 365
        if calendar.isleap(DateTime().parts()[0]): days += 1
        self.daysdown = map(lambda x: 0, range(days)) 


    def addDaily(self, dailydown):
        """add the daily down time for a day"""
        self.daysdown.insert(DateTime().dayOfYear()-1, dailydown) 
        self._p_changed = 1
       

    def getDownTime(self, start=None, end=None):
        """get the down time in seconds over a date range, dates are DateTime"""
        if end == None: 
            end = len(self.daysdown)
        elif isinstance(end, DateTime):
            end = end.dayOfYear()
        if start == None: 
            start=1
        elif isinstance(start, DateTime):
            start = start.dayOfYear()
        start -= 1 
        return sum(self.daysdown[start:end])
