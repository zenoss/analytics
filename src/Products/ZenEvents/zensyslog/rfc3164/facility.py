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


class Facility(IntEnum):
    kernel = 0
    user = 1
    mail = 2
    system = 3
    security4 = 4
    syslogd = 5
    printer = 6
    network_news = 7
    uucp = 8
    clock9 = 9
    security10 = 10
    ftp = 11
    ntp = 12
    log_audit = 13
    log_alert = 14
    clock15 = 15
    local0 = 16
    local1 = 17
    local2 = 18
    local3 = 19
    local4 = 20
    local5 = 21
    local6 = 22
    local7 = 23

    @property
    def description(self):
        return _descriptions.get(self.value)


_descriptions = {
    0: "kernel messages",
    1: "user-level messages",
    2: "mail system",
    3: "system daemons",
    4: "security/authorization messages",
    5: "messages generated internally by syslogd",
    6: "line printer subsystem",
    7: "network news subsystem",
    8: "UUCP subsystem",
    9: "clock daemon",
    10: "security/authorization messages",
    11: "FTP daemon",
    12: "NTP subsystem",
    13: "log audit",
    14: "log alert",
    15: "clock daemon",
    16: "local use 0  (local0)",
    17: "local use 1  (local1)",
    18: "local use 2  (local2)",
    19: "local use 3  (local3)",
    20: "local use 4  (local4)",
    21: "local use 5  (local5)",
    22: "local use 6  (local6)",
    23: "local use 7  (local7)",
}
