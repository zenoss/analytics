##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import re
import time

from collections import Sequence

import six

from Products.ZenEvents.EventServer import Stats
from Products.ZenEvents.ZenEventClasses import Error
from Products.ZenUtils.IpUtil import isip

from . import rfc3164

log = logging.getLogger("zen.zensyslog.processor")


class SyslogProcessor(object):
    """
    Class to process syslog messages and convert them into events viewable
    in the Zenoss event console.
    """

    def __init__(
        self,
        sendEvent,
        minpriority,
        parsehost,
        monitor,
        parsers,
    ):
        """
        Initialize a SyslogProcessor instance.

        @param sendEvent: message from a remote host
        @type sendEvent: string
        @param minpriority: ignore anything under this priority
        @type minpriority: integer
        @param parsehost: hostname where this parser is running
        @type parsehost: string
        @param monitor: name of the distributed collector monitor
        @type monitor: string
        @param defaultPriority: priority to use if it can't be understood
            from the received packet
        @type defaultPriority: integer
        @param syslogParsers: configureable syslog parsers
        @type defaultPriority: list
        """
        self.minpriority = minpriority
        self.parsehost = parsehost
        self.sendEvent = sendEvent
        self.monitor = monitor
        self.parsers = parsers

        # These are set as found on the EventManagerBase class.
        self.use_summary = False
        self._severity = rfc3164.Severity.Error

        self.stats = Stats()

    @property
    def priority(self):
        """Return the default syslog severity value."""
        return self._severity.value

    @priority.setter
    def priority(self, value):
        self._severity = rfc3164.Severity(value)

    def process(self, msg, ipaddr, host, rtime):
        """
        Process an event from syslog and convert to a Zenoss event

        Returns either "EventSent" or "ParserDropped"

        @param msg: message from a remote host
        @type msg: string
        @param ipaddr: IP address of the remote host
        @type ipaddr: string
        @param host: remote host's name
        @type host: string
        @param rtime: time as reported by the remote host
        @type rtime: string
        """
        try:
            fac, sev, dt, hostname, mesg = self._parse_message(msg)
        except rfc3164.SyslogMessageError as ex:
            log.error("bad syslog message: %s", ex)
            return

        # Lower values mean higher severity/priority
        if sev.value > self.minpriority:
            log.debug("syslog severity below minimum  value=%s", sev.value)
            return

        event, drop = self._build_event(mesg, host, ipaddr, rtime, fac, sev)
        if drop:
            return drop

        self._maybe_add_originalTime(event, dt)
        self._maybe_add_device(event, hostname)
        self._maybe_use_summary_for_message(event, mesg)
        self._maybe_overwrite_severity(event)
        self._maybe_add_eventclasskey_value(event)
        self._maybe_add_message(event, mesg)

        self._convert_to_unicode(event)

        self.sendEvent(event)
        self.stats.add(time.time() - rtime)
        return "EventSent"

    def _parse_message(self, message):
        fac, sev, dt, hostname, mesg = rfc3164.parse(message)

        # Use default severity if a severity was not found in message
        sev = sev if sev else self._severity

        return (fac, sev, dt, hostname, mesg)

    def _build_event(self, mesg, host, ipaddr, rtime, fac, sev):
        fields, index, drop = parse_MSG(mesg, self.parsers)
        if drop:
            return (None, "ParserDropped")

        event = {
            "device": host,
            "monitor": self.monitor,
            "ipAddress": ipaddr,
            "firstTime": rtime,
            "lastTime": rtime,
            "eventGroup": "syslog",
            "facility": fac.value if fac else None,
            "priority": sev.value,
            "severity": sev.as_event_severity(),
            "parserRuleMatched": index,
        }
        event.update(fields)
        return (event, None)

    def _maybe_add_originalTime(self, event, dt):
        if dt:
            event["originalTime"] = dt.strftime("%b %d %H:%M:%S")

    def _maybe_add_device(self, event, hostname):
        if self.parsehost and hostname:
            event["device"] = hostname
            if isip(hostname):
                event["ipAddress"] = hostname
            else:
                del event["ipAddress"]

    def _maybe_use_summary_for_message(self, event, mesg):
        if self.use_summary:
            event["message"] = event.get("summary", "")
            event["unparsedMessage"] = mesg

    def _maybe_overwrite_severity(self, event):
        if "overwriteSeverity" not in event:
            return
        overwrite_v = int(event["overwriteSeverity"])
        overwrite = rfc3164.Severity(overwrite_v)
        old_severity = event["severity"]
        new_severity = overwrite.as_event_severity()
        log.debug(
            "Severity overwritten in message tag. Previous:%s Current:%s",
            old_severity,
            new_severity,
        )
        event["severity"] = new_severity

    def _maybe_add_eventclasskey_value(self, event):
        value = getEventClassKeyValue(event)
        if value:
            event["eventClassKey"] = value

    def _maybe_add_message(self, event, mesg):
        if "message" not in event:
            event["message"] = mesg

    def _convert_to_unicode(self, event):
        # Convert strings to unicode, previous code converted 'summary' &
        # 'message' fields. With parsing group name matching, good idea to
        # convert all fields.
        event.update(
            {
                k: six.text_type(v)
                for k, v in event.iteritems()
                if isinstance(v, six.binary_type)
            }
        )


def parse_MSG(msg, parsers):
    """
    Parse the RFC-3164 tag of the syslog message using the regex defined
    at the top of this module.

    @param msg: message from host
    @type msg: string
    @return: dictionary of event properties
    @type: dictionary
    """
    log.debug("[parsed_Tag] message=%s", msg)
    fields = {}
    for i, parser in enumerate(parsers):
        log.debug("parser[%s] regex: %s", i, parser.pattern)
        result = parser.parse(msg)
        if result is None:
            continue
        if not parser.keep:
            log.debug(
                "parser[%s] matched but DROPPED due to parser. "
                "msg:%r, pattern:%r, parsedGroups:%r",
                i,
                msg,
                parser.pattern,
                result,
            )
            return None, -1, True
        log.debug(
            "parser[%s] matched. msg:%r, pattern:%r, parsedGroups:%r",
            i,
            msg,
            parser.pattern,
            result,
        )
        return result, i, False
    else:
        log.debug("No matching parser: %r", msg)
        fields["summary"] = msg
        return fields, -1, False


def getEventClassKeyValue(evt):
    """
    Build the key used to find an events dictionary record. If eventClass
    is defined it is used. For NT events "Source_Evid" is used. For other
    syslog events we use the summary of the event to perform a full text
    or'ed search.

    @param evt: dictionary of event properties
    @type evt: dictionary
    @return: dictionary of event properties
    @type: dictionary
    """
    if "eventClassKey" in evt or "eventClass" in evt:
        return None

    if "ntevid" in evt:
        value = "{component}_{ntevid}".format(**evt)
    elif "component" in evt:
        value = evt["component"]
    else:
        value = None

    if value:
        try:
            value = value.decode("latin-1")
        except Exception:
            value = value.decode("utf-8")

    return value


_parser_error_event = {
    "device": "127.0.0.1",
    "eventClass": "/App/Zenoss",
    "severity": Error,
    "eventClassKey": "",
    "summary": "Syslog Parser processing issue",
    "component": "zensyslog",
}


class _Parser(object):
    __slots__ = ("_matcher", "keep")

    def __init__(self, matcher, keep):
        self._matcher = matcher
        self.keep = keep

    @property
    def pattern(self):
        return self._matcher.pattern

    def parse(self, text):
        m = self._matcher.search(text)
        return m.groupdict() if m else None


class Parsers(Sequence):
    def __init__(self, sendevent):
        self._sendevent = sendevent
        self._parsers = []

    def __getitem__(self, offset):
        return self._parsers[offset]

    def __len__(self):
        return len(self._parsers)

    def update(self, source):
        parsers = []
        for idx, spec in enumerate(source):
            if "expr" not in spec:
                msg = (
                    'Parser configuration #{} missing a "expr" attribute'
                ).format(idx)
                log.warn(msg)
                self._send_error_event(message=msg)
                continue
            try:
                matcher = re.compile(spec["expr"], re.DOTALL)
                parser = _Parser(matcher, spec["keep"])
            except Exception as ex:
                msg = (
                    "Parser configuration #{} Could not compile expression "
                    '"{!r}", {!r}'
                ).format(idx, spec["expr"], ex)
                log.warn(msg)
                self._send_error_event(message=msg)
            else:
                parsers.append(parser)
        self._parsers[:] = parsers

    def _send_error_event(self, **kwargs):
        """
        Build an Event dict from parameters.n
        """
        if kwargs:
            event = _parser_error_event.copy()
            event.update(kwargs)
        else:
            event = _parser_error_event
        self._sendevent(event)
