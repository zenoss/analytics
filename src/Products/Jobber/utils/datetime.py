##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import


class TimeDeltaStruct(object):

    __slots__ = (
        "weeks",
        "days",
        "hours",
        "minutes",
        "seconds",
    )

    @classmethod
    def from_timedelta(cls, td):
        weeks = td.days // _days_per_week
        days = td.days % _days_per_week

        hours = td.seconds // _secs_per_hour
        secs_remaining = td.seconds % _secs_per_hour

        minutes = secs_remaining // _secs_per_minute
        seconds = secs_remaining % _secs_per_minute

        return cls(
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
        )

    def __init__(self, weeks=0, days=0, hours=0, minutes=0, seconds=0):
        self.weeks = weeks
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds


_days_per_week = 7
_secs_per_hour = 3600
_secs_per_minute = 60


def humanize_timedelta(td):
    tds = TimeDeltaStruct.from_timedelta(td)
    text = []
    if tds.weeks > 0:
        text.append("{} weeks".format(tds.weeks))
    if tds.days > 0:
        text.append("{} days".format(tds.days))
    if tds.hours > 0:
        text.append("{} hours".format(tds.hours))
    if tds.minutes > 0:
        text.append("{} minutes".format(tds.minutes))
    if tds.seconds > 0:
        text.append("{} seconds".format(tds.seconds))
    if len(text) == 0:
        return "immediately"
    return ", ".join(text)
