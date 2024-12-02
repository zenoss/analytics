##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""Time

Utilities for consistent manipulation of Dates and Time.  All simple
code should migrate here, and without dependencies on anything other
than standard python libraries.

$Id:$"""

__version__ = "$$"[11:-2]

import time
import os
import pytz
import dateutil.tz as tz
import re
from datetime import datetime
from hashlib import sha224
from math import isnan

def _maybenow(gmtSecondsSince1970):
    if gmtSecondsSince1970 is None:
        return time.time()
    return int(gmtSecondsSince1970)

def LocalDateTime(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    secs = value % 60
    return time.strftime("%Y/%m/%d %H:%M:%%06.3f", time.localtime(value)) % secs

def LocalDateTimeFromMilli(milliseconds):
    """
    @param milliseconds:: UTC timestamp in milliseconds
    """
    return LocalDateTime(milliseconds / 1000)

def convertJsTimeFormatToPy(fmt):
    d = {'YYYY': '%Y', 'MM': '%m', 'DD': '%d',
         'HH': '%H', 'hh': '%I', 'mm': '%M',
         'ss': '%S', 'a': '%p'}
    pattern = re.compile(r'\b(' + '|'.join(d.keys()) + r')\b')
    return pattern.sub(lambda x: d[x.group()], fmt)

def convertTimestampToTimeZone(timestamp, zone_name, fmt="%Y/%m/%d %H:%M:%S"):
    """
    This takes a integer timestamp (in seconds since epoch) and returns a
    string that represents the time in the timezone name in the provided format.
    """    
    utc_tz = pytz.timezone('UTC')
    utc_dt = utc_tz.localize(datetime.utcfromtimestamp(timestamp))
    try:
        localized_tz = pytz.timezone(zone_name)
    except pytz.UnknownTimeZoneError:
        # return server time
        return isoDateTime(timestamp, fmt)     
    localized_dt = localized_tz.normalize(utc_dt.astimezone(localized_tz))
    return localized_dt.strftime(fmt)
    
def isoDateTime(gmtSecondsSince1970 = None, fmt="%Y-%m-%d %H:%M:%S"):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime(fmt, time.localtime(value))

def isoDateTimeFromMilli(milliseconds):
    """
    @param milliseconds:: UTC timestamp in milliseconds
    """
    return isoDateTime(milliseconds / 1000)

def LocalDateTimeSecsResolution(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(value))

def USDate(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%m/%d/%Y", time.localtime(value))

def ParseUSDate(mdy):
    return time.mktime(time.strptime(mdy, "%m/%d/%Y"))

def YYYYMMDDHHMMS(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%Y%m%d%H%M%S", time.localtime(value))

def HHMMSS(gmtSecondsSince1970 = None):
    value = _maybenow(gmtSecondsSince1970)
    return time.strftime("%H:%M:%S", time.localtime(value))

def SaveMessage():
    return "Saved at time: " + HHMMSS()

def Duration(seconds):
    if isnan(seconds):
        return "nan"

    seconds = int(seconds)
    result = ':%02d' % (seconds % 60)
    seconds /= 60
    if seconds:
        result = '%02d%s' % (seconds % 60, result)
    seconds /= 60
    if seconds:
        result = '%02d:%s' % (seconds % 24, result)
    seconds /= 24
    if seconds:
        result = '%d days %s' % (seconds, result)
    return result


def getBeginningOfDay(gmtSecondsSince1970=None):
    value = _maybenow(gmtSecondsSince1970)
    return time.mktime(time.localtime(value)[:3] + (0,0,0,0,0,-1))


def getEndOfDay(gmtSecondsSince1970=None):
    value = _maybenow(gmtSecondsSince1970)
    return time.mktime(time.localtime(value)[:3] + (23,59,59,0,0,-1))

def isoToTimestamp(value):
    """
    converts a iso time string that does not contain a timezone, ie.
    YYYY-MM-DD HH:MM:SS, to a timestamp in seconds since 1970; uses the system
    timezone
    """
    timeStr = value.replace('T', ' ')
    timeTuple = time.strptime(timeStr, '%Y-%m-%d %H:%M:%S')
    timestamp = time.mktime(timeTuple)
    return timestamp

def awareDatetimeToTimestamp(awareDatetime):
    """
    converts a datetime that contains a timezone to a timestamp in seconds since 1970
    """
    return (awareDatetime.astimezone(tz.tzutc()) - datetime(1970, 1, 1, tzinfo=tz.tzutc())).total_seconds()

def getYear():
    """
    Return a string representing the current year.
    """
    return datetime.now().strftime('%Y')

def getLocalTimezone():
    """
    Return a string representing local time zone.
    """
    # try to read serviced variable
    timezone = os.getenv("TZ", None)

    if not timezone:
        timezone = time.strftime("%Z")

    return timezone
    
