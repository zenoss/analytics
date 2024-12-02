##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import time

from Products.ZenUtils.Utils import zenPath

SYSLOG_DATE_FORMAT = "%b %d %H:%M:%S"
SAMPLE_DATE = "Apr 10 15:19:22"


class DropLogger(object):
    """
    Messages are not written anywhere.
    """

    def log(self, message, address):
        pass


class MessageLogger(object):
    """
    Writes syslog messages to a log file.
    """

    def __init__(self, formatter):
        self._formatter = formatter
        self._log = _get_logger()

    def log(self, data, address):
        message = self._formatter(data, address)
        self._log.info(message)


def _get_logger(self):
    log = logging.getLogger("origsyslog")
    log.setLevel(logging.INFO)
    log.propagate = False
    filepath = zenPath("log', 'origsyslog.log")
    handler = logging.FileHandler(filepath)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    return log


class RawFormatter(object):
    def __call__(self, data, address):
        return data


class HumanFormatter(object):
    """
    Expands a syslog message into a string format suitable for writing
    to the filesystem such that it appears the same as it would
    had the message been logged by the syslog daemon.

    @param msg: syslog message
    @type msg: string
    @param client_address: IP info of the remote device (ipaddr, port)
    @type client_address: tuple of (string, number)
    @return: message
    @rtype: string
    """

    def __call__(self, data, address):
        # pri := (facility * 8) + severity
        stop = data.find(">")

        # check for a datestamp.  default to right now if date not present
        start = stop + 1
        stop = start + len(SAMPLE_DATE)
        dateField = data[start:stop]
        try:
            date = time.strptime(dateField, SYSLOG_DATE_FORMAT)
            year = time.localtime()[0]
            date = (year,) + date[1:]
            start = stop + 1
        except ValueError:
            # date not present, so use today's date
            date = time.localtime()

        # check for a hostname.  default to localhost if not present
        stop = data.find(" ", start)
        if data[stop - 1] == ":":
            hostname = address[0]
        else:
            hostname = data[start:stop]
            start = stop + 1

        # the message content
        body = data[start:]

        # assemble the message
        prettyTime = time.strftime(SYSLOG_DATE_FORMAT, date)
        message = "%s %s %s" % (prettyTime, hostname, body)
        return message
