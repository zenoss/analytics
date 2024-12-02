##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import base64
import logging
import socket
import time

from struct import unpack

import six

log = logging.getLogger("zen.zentrap")


def decode_snmp_value(value):
    """Given a raw OID value
    Itterate over the list of decoder methods in order
    Returns the first value returned by a decoder method
    """
    if value is None:
        return value
    try:
        for decoder in _decoders:
            out = decoder(value)
            if out is not None:
                return out
    except Exception as err:
        log.exception("Unexpected exception: %s", err)


def dateandtime(value):
    """Tries converting a DateAndTime value to a printable string.

    A date-time specification.
    field  octets  contents                  range
    -----  ------  --------                  -----
    1      1-2     year*                     0..65536
    2        3     month                     1..12
    3        4     day                       1..31
    4        5     hour                      0..23
    5        6     minutes                   0..59
    6        7     seconds                   0..60
                  (use 60 for leap-second)
    7        8     deci-seconds              0..9
    8        9     direction from UTC        '+' / '-'
    9       10     hours from UTC*           0..13
    10      11     minutes from UTC          0..59
    """
    try:
        dt, tz = value[:8], value[8:]
        if len(dt) != 8 or len(tz) != 3:
            return None
        (year, mon, day, hour, mins, secs, dsecs) = unpack(">HBBBBBB", dt)
        # Ensure valid date representation
        invalid = (
            (mon < 1 or mon > 12),
            (day < 1 or day > 31),
            (hour > 23),
            (mins > 59),
            (secs > 60),
            (dsecs > 9),
        )
        if any(invalid):
            return None
        (utc_dir, utc_hour, utc_min) = unpack(">cBB", tz)
        # Some traps send invalid UTC times (direction is 0)
        if utc_dir == "\x00":
            tz_min = time.timezone / 60
            if tz_min < 0:
                utc_dir = "-"
                tz_min = -tz_min
            else:
                utc_dir = "+"
            utc_hour = tz_min / 60
            utc_min = tz_min % 60
        if utc_dir not in ("+", "-"):
            return None
        return "%04d-%02d-%02dT%02d:%02d:%02d.%d00%s%02d:%02d" % (
            year,
            mon,
            day,
            hour,
            mins,
            secs,
            dsecs,
            utc_dir,
            utc_hour,
            utc_min,
        )
    except TypeError:
        pass


def oid(value):
    if (
        isinstance(value, tuple)
        and len(value) > 2
        and value[0] in (0, 1, 2)
        and all(isinstance(i, int) for i in value)
    ):
        return ".".join(map(str, value))


def number(value):
    return value if isinstance(value, six.integer_types) else None


def ipaddress(value):
    for version in (socket.AF_INET, socket.AF_INET6):
        try:
            return socket.inet_ntop(version, value)
        except (ValueError, TypeError):
            pass


def utf8(value):
    try:
        return value.decode("utf8")
    except (UnicodeDecodeError, AttributeError):
        pass


def encode_base64(value):
    return "BASE64:" + base64.b64encode(value)


# NOTE: The order of decoders in the list determines their priority
_decoders = [
    oid,
    number,
    utf8,
    ipaddress,
    dateandtime,
    encode_base64,
]
