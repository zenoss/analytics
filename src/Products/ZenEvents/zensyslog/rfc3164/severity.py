##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from enum import IntEnum

from Products.ZenEvents import ZenEventClasses as _zec


class Severity(IntEnum):
    Emergency = 0
    Alert = 1
    Critical = 2
    Error = 3
    Warning = 4
    Notice = 5
    Informational = 6
    Debug = 7

    @property
    def description(self):
        return _descriptions.get(self.value)

    def as_event_severity(self):
        return _syslog_to_zenoss.get(self.value)


_descriptions = {
    0: "system is unusable",
    1: "action must be taken immediately",
    2: "critical conditions",
    3: "error conditions",
    4: "warning conditions",
    5: "normal but significant condition",
    6: "informational messages",
    7: "debug-level messages",
}

_syslog_to_zenoss = {
    0: _zec.Critical,
    1: _zec.Critical,
    2: _zec.Critical,
    3: _zec.Error,
    4: _zec.Warning,
    5: _zec.Info,
    6: _zec.Info,
    7: _zec.Debug,
}
