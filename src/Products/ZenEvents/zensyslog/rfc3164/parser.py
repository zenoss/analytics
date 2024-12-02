##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import re

import dateutil.parser

from .facility import Facility
from .severity import Severity

log = logging.getLogger("zen.zensyslog.parser")


class SyslogMessageError(ValueError):
    """Raised when the syslog message has bad values"""


def parse(message):
    """
    Return a parsed syslog (RFC 3164) message.

    Return a tuple having four elements:

        (facility, severity, datetime, hostname, message)

    The 'message' is the remaining content of the original message
    minus the 'facility', 'severity', 'datetime', and 'hostname' parts.
    """
    start = 0
    start, facility, severity = _extract_pri(start, message)
    start, dt = _extract_timestamp(start, message)
    start, hostname = _extract_hostname(start, message)
    return (facility, severity, dt, hostname, message[start:].strip())


def _extract_pri(start, mesg):
    """
    Parse RFC-3164 PRI part of syslog message to get facility and priority.

    Returns a tuple containing a dict of the parsed fields and unparsed
    portion of the syslog message string.

    @param msg: message from host
    @type msg: string
    @return: tuple of dictionary of event properties and the message
    @type: (dictionary, string)
    """
    if mesg[start:1] == "<":
        posn = mesg.find(">")
        pvalue = mesg[start + 1 : posn]
        try:
            pvalue = int(pvalue)
        except ValueError:
            raise SyslogMessageError(
                "Found '{}' instead of a number for priority".format(pvalue)
            )
        fac, sev = divmod(pvalue, 8)
        try:
            facility = Facility(fac)
        except ValueError:
            raise SyslogMessageError("Invalid facility value '{}'".format(fac))
        try:
            severity = Severity(sev)
        except ValueError:
            raise SyslogMessageError("Invalid severity value '{}'".format(sev))
        return (posn + 1, facility, severity)

    if mesg and mesg[start] < " ":
        sev = ord(mesg[start])
        try:
            severity = Severity(sev)
        except ValueError:
            raise SyslogMessageError("Invalid severity value '{}'".format(sev))
        return (start + 1, Facility.kernel, severity)

    log.debug("no priority found in message")
    return (start, None, None)


_match_timestamp = re.compile(
    "^(\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[\d ]{2}(?:\.\d{1,3})?)", re.DOTALL
).search


def _extract_timestamp(start, mesg):
    m = _match_timestamp(mesg[start:])
    if not m:
        log.debug("no timestamp found in message")
        return (start, None)
    ts = m.group(0)
    try:
        dt = dateutil.parser.parse(ts)
    except ValueError:
        raise SyslogMessageError("Invalid timestamp '{}'".format(ts))
    else:
        return (start + len(ts) + 1, dt)


_not_hostname = re.compile(r"[\[:]").search


def _extract_hostname(start, mesg):
    offset = mesg[start:].find(" ")
    if offset < 0:
        log.debug("unexpected end of message")
        return start, None
    hostname = mesg[start : start + offset]
    if _not_hostname(hostname):
        log.debug("no hostname found in message")
        return start, None
    hostname = hostname.split("@", 1)[-1]
    return (start + offset), hostname
