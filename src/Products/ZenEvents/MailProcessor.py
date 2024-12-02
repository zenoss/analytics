##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """MailProcessor
Base class module that other servers will subclass.
"""

import logging
log = logging.getLogger("zen.mail")

import re
import email
import time
import socket
import rfc822
import calendar
from datetime import tzinfo, timedelta, datetime


from Products.ZenEvents.Event import Event
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.ZenScriptBase import ZenScriptBase


class MailEvent(Event):
    """
    Defaults for events created by the processor
    """
    agent = "zenmail"
    eventGroup = "mail"


# The following is copied from the Python standard library
# examples page: http://docs.python.org/library/datetime.html
ZERO = timedelta(0)

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.
# FIXME: Python docs suggest using IANA timezone database via pytz class
class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, unused):
        return self.__offset

    def tzname(self, unused):
        return self.__name

    def dst(self, dt):
        return ZERO


class MessageProcessor(object):
    """
    Base class for parsing email messages that are retrieved via POP or
    received via SMTP.
    """

    def __init__(self, zem, defaultSeverity = 2):
        """
        Initializer

        @param zem: class that provides sendEvent() method
        @type zem: Zenoss event manager object
        @param defaultSeverity: severity level to use if we can't figure one out
        @type defaultSeverity: integer
        """
        self.zem = zem
        self.eventSeverity = defaultSeverity
        self.one_part_email = re.compile(r'''^[<"']?(.*?)[">']?$''')
        self.two_part_email = re.compile(r'(.*) <(.*?)>$')

    def parse_email_address(self, address):
        address = address.replace('\n', '').replace('\t', ' ')
        match = self.two_part_email.match(address)
        if match:
            return self.parse_email_address(match.group(2))
        match = self.one_part_email.match(address)
        if match:
            return match.group(1)

    def process(self, messageStr):
        """
        Convert an e-mail message into a Zenoss event.

        @param messageStr: e-mail message
        @type messageStr: string
        """
        message = email.message_from_string(messageStr)
        self.message = message

        fromAddr = message.get('From')
        origFromAddr = fromAddr
        log.debug("Found a 'from' address of %s", fromAddr)
        if not fromAddr or fromAddr.find('@') == -1:
            log.warning("Unable to process the 'from' address %s -- ignoring mail", fromAddr)
            return

        fromAddr = self.parse_email_address(fromAddr)
        if not fromAddr:
            log.warning("Could not parse email address in the 'from' address %s -- ignoring mail",
                        origFromAddr)
            return
        log.debug("The from address after processing is '%s'", fromAddr)
        fromHost = fromAddr.split('@')[-1]
        try:
            fromIp = socket.gethostbyname(fromHost)
        except socket.gaierror:
            fromIp = None
            log.info('Hostname lookup failed for host: %s', fromHost)

        subject = message.get('Subject').replace("\r","").replace("\n", "")

        secs = self.getReceiveTime(message)

        event = MailEvent(device=fromHost, rcvtime=secs,
                          fromEmailAddress=origFromAddr)
        if fromIp:
            event.ipAddress = fromIp

        payload = 'This is the default message'
        if message.is_multipart():
            for msg in message.get_payload():
                if msg.get_content_maintype() == 'text' or msg.get_content_type() == 'message/rfc822':
                    payload = msg.get_payload(decode=True)
                    break
        else:
            payload = message.get_payload(decode=True)

        body = payload
        event.summary = subject
        event.message = body
        self.enrich(event, subject)

        event = self.buildEventClassKey(event)
        self.zem.sendEvent(event.__dict__)

    def enrich(self, event, subject):
        """
        Sanitize the event facility and severity fields.

        @param event: event
        @type event: simple class
        @param subject: e-mail subject (unused)
        @type subject: string
        """
        unused(subject)
        event.facility = "unknown"
        event.severity = self.eventSeverity

    def buildEventClassKey(self, evt):
        """
        Set the Zenoss eventClassKey

        @param evt: event
        @type evt: simple class
        @return: modified event
        @rtype: simple class
        """
        if getattr(evt, 'eventClassKey', '') or getattr(evt, 'eventClass', ''):
            return evt
        elif getattr(evt, 'ntevid', ''):
            evt.eventClassKey = "%s_%s" % (evt.component,evt.ntevid)
        elif getattr(evt, 'component', ''):
            evt.eventClassKey = evt.component
        else:
            evt.eventClassKey = 'email'

        if getattr(evt, 'eventClassKey', ''):
            log.debug("eventClassKey=%s", evt.eventClassKey)
        else:
            log.debug("No eventClassKey assigned")
        return evt

    def getReceiveTime(self, message):
        # This is tricky...  date comes in with an offset value that
        # represents the number of seconds of difference between the
        # parsed timezone and UTC.  The events database wants all time
        # as seconds since the epoch and treats it as UTC.  As a
        # result we have to use the datetime class to do the
        # conversion because the functions in the time module do all
        # kinds of conversions "to be helpful"
        timestamp = message.get('Date', message.get('Sent'))
        t = rfc822.parsedate_tz(timestamp)
        if t is None:
            log.warn("Unable to process timestamp '%s' -- defaulting to now",
                     timestamp)
            return time.time()

        offset_secs = t[-1]
        if offset_secs is not None:
            # Convert the offset in seconds to minutes.  calendar wants minutes
            offset_mins = offset_secs / 60
            tz = FixedOffset(offset_mins, "Unknown")
        else:
            log.warn("Timezone not specified in '%s' -- defaulting to local timezone",
                     timestamp)
            tz = None

        # Construct dt using the date and time as well as the timezone
        dt = datetime(t[0], t[1], t[2], t[3], t[4], t[5], 0, tz)
        secs = calendar.timegm(dt.utctimetuple())
        log.debug('Timestamp of the event (should be in UTC): %s -> %f',
                  timestamp, secs)
        return secs


class POPProcessor(MessageProcessor):
    """
    Extension point for messages received via POP.  If you need to
    override the behavior of "process" you should do so by
    implementing it here.
    """

    def __init__(self, zem, defaultSeverity = 2):
        """
        Initializer

        @param zem: class that provides sendEvent() method
        @type zem: Zenoss event manager object
        @param defaultSeverity: severity level to use if we can't figure one out
        """
        MessageProcessor.__init__(self, zem, defaultSeverity)


class MailProcessor(MessageProcessor):
    """
    Extension point for messages received via SMTP.  If you need to
    override the behavior of "process" you should do so by
    implementing it here.
    """

    def __init__(self, zem, defaultSeverity = 2):
        """
        Initializer

        @param zem: class that provides sendEvent() method
        @type zem: Zenoss event manager object
        @param defaultSeverity: severity level to use if we can't figure one out
        """
        MessageProcessor.__init__(self, zem, defaultSeverity)


class ZenMailTest(ZenScriptBase):
    """
    Usage:

    python MailProcessor.py file1 [...]

    Read text files that are saved emails and send events into Zenoss
    """
    def __init__(self):
        ZenScriptBase.__init__(self, connect=True)

    def run(self):
        if len(self.args) == 0:
            log.critical("Need at least one input filename!")
            sys.exit(1)

        mp = MessageProcessor(self.dmd.ZenEventManager)

        for emailFile in self.args:
            try:
                email = open(emailFile).read()
            except Exception as ex:
                log.error("Unable to open %s: %s", emailFile, ex)
                continue
            mp.process(email)


if __name__ == '__main__':
    import sys

    zmt = ZenMailTest()
    zmt.run()

