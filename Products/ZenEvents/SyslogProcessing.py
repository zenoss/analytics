##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """SyslogProcessing
Class for turning syslog events into Zenoss Events
"""

import re
import logging
slog = logging.getLogger("zen.Syslog")
import socket

from Products.ZenEvents.syslog_h import *
from Products.ZenUtils.IpUtil import isip


# Regular expressions that parse syslog tags from different sources
# A tuple can also be specified, in which case the second item in the
# tuple is a boolean which tells whether or not to keep the entry (default)
# or to discard the entry and not create an event.
parsers = (
# generic mark
r"^(?P<summary>-- (?P<eventClassKey>MARK) --)",

# Cisco UCS
# : 2010 Oct 19 15:47:45 CDT: snmpd: SNMP Operation (GET) failed. Reason:2 reqId (257790979) errno (42) error index (1)
r'^: \d{4} \w{3}\s+\d{1,2}\s+\d{1,2}:\d\d:\d\d \w{3}: %(?P<eventClassKey>[^:]+): (?P<summary>.*)',

# ntsyslog windows msg
r"^(?P<component>.+)\[(?P<ntseverity>\D+)\] (?P<ntevid>\d+) (?P<summary>.*)",

# cisco msg with card indicator
r"%CARD-\S+:(SLOT\d+) %(?P<eventClassKey>\S+): (?P<summary>.*)",

# cisco standard msg
r"%(?P<eventClassKey>(?P<component>\S+)-(?P<overwriteSeverity>\d)-\S+): *(?P<summary>.*)",

# Cisco ACS
r"^(?P<ipAddress>\S+)\s+(?P<summary>(?P<eventClassKey>(CisACS_\d\d|CSCOacs)_\S+)\s+(?P<eventKey>\S+)\s.*)",

# netscreen device msg
r"device_id=\S+\s+\[\S+\](?P<eventClassKey>\S+\d+):\s+(?P<summary>.*)\s+\((?P<originalTime>\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)\)",

# NetApp
# [deviceName: 10/100/1000/e1a:warning]: Client 10.0.0.101 (xid 4251521131) is trying to access an unexported mount (fileid 64, snapid 0, generation 6111516 and flags 0x0 on volume 0xc97d89a [No volume name available])
r"^\[[^:]+: (?P<component>[^:]+)[^\]]+\]: (?P<summary>.*)",

# unix syslog with pid
r"(?P<component>\S+)\[(?P<pid>\d+)\]:\s*(?P<summary>.*)",

# unix syslog without pid
r"(?P<component>\S+): (?P<summary>.*)",

# adtran devices
r"^(?P<deviceModel>[^\[]+)\[(?P<deviceManufacturer>ADTRAN)\]:(?P<component>[^\|]+\|\d+\|\d+)\|(?P<summary>.*)",

r"^date=.+ (?P<summary>devname=.+ log_id=(?P<eventClassKey>\d+) type=(?P<component>\S+).+)",

# proprietary message passing system
r"^(?P<component>\S+)(\.|\s)[A-Z]{3} \d \S+ \d\d:\d\d:\d\d-\d\d:\d\d:\d\d \d{5} \d{2} \d{5} \S+ \d{4} \d{3,5} (- )*(?P<summary>.*) \d{4} \d{4}",

# Cisco port state logging info
r"^Process (?P<process_id>\d+), Nbr (?P<device>\d+\.\d+\.\d+\.\d+) on (?P<interface>\w+/\d+) from (?P<start_state>\w+) to (?P<end_state>\w+), (?P<summary>.+)",

# Cisco VPN Concentrator
# 54884 05/25/2009 13:41:14.060 SEV=3 HTTP/42 RPT=4623 Error on socket accept.
r"^\d+ \d+\/\d+\/\d+ \d+:\d+:\d+\.\d+ SEV=\d+ (?P<eventClassKey>\S+) RPT=\d+ (?P<summary>.*)",

# Dell Storage Array
# 2626:48:VolExec:27-Aug-2009 13:15:58.072049:VE_VolSetWorker.hh:75:WARNING:43.3.2:Volume volumeName has reached 96 percent of its reported size and is currently using 492690MB.
r'^\d+:\d+:(?P<component>[^:]+):\d+-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d+:[^:]+:\d+:\w+:(?P<eventClassKey>[^:]+):(?P<summary>.*)',

# 1-Oct-2009 23:00:00.383809:snapshotDelete.cc:290:INFO:8.2.5:Successfully deleted snapshot 'UNVSQLCLUSTERTEMPDB-2009-09-30-23:00:14.11563'.
r'^\d+-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d+:[^:]+:\d+:\w+:(?P<eventClassKey>[^:]+):(?P<summary>.*)',
)

# compile regex parsers on load
compiledParsers = []
for regex in parsers:
    keepEntry = True
    if isinstance(regex, tuple):
        regex, keepEntry = regex
    try:
        compiled = re.compile(regex, re.DOTALL)
        compiledParsers.append((compiled, keepEntry))
    except Exception:
        pass


class SyslogProcessor(object):
    """
    Class to process syslog messages and convert them into events viewable
    in the Zenoss event console.
    """

    def __init__(self,sendEvent,minpriority,parsehost,monitor,defaultPriority):
        """
        Initializer

        @param sendEvent: message from a remote host
        @type sendEvent: string
        @param minpriority: ignore anything under this priority
        @type minpriority: integer
        @param parsehost: hostname where this parser is running
        @type parsehost: string
        @param monitor: name of the distributed collector monitor
        @type monitor: string
        @param defaultPriority: priority to use if it can't be understood from the received packet
        @type defaultPriority: integer
        """
        self.minpriority = minpriority
        self.parsehost = parsehost
        self.sendEvent = sendEvent
        self.monitor = monitor
        self.defaultPriority = defaultPriority


    def process(self, msg, ipaddr, host, rtime):
        """
        Process an event from syslog and convert to a Zenoss event

        @param msg: message from a remote host
        @type msg: string
        @param ipaddr: IP address of the remote host
        @type ipaddr: string
        @param host: remote host's name
        @type host: string
        @param rtime: time as reported by the remote host
        @type rtime: string
        """
        evt = dict(device=host,
                   ipAddress=ipaddr,
                   firstTime=rtime,
                   lastTime=rtime,
                   eventGroup='syslog')
        slog.debug("host=%s, ip=%s", host, ipaddr)
        slog.debug(msg)

        evt, msg = self.parsePRI(evt, msg)
        if evt['priority'] > self.minpriority: return

        evt, msg = self.parseHEADER(evt, msg)
        evt = self.parseTag(evt, msg)
        if evt:
            # Cisco standard msg includes the severity in the tag
            if 'overwriteSeverity' in evt.keys():
                old_severity = evt['severity']
                new_severity = self.defaultSeverityMap(int(evt['overwriteSeverity']))
                evt['severity'] = new_severity
                slog.debug('Severity overwritten in message tag. Previous:%s Current:%s', old_severity, new_severity)
            #rest of msg now in summary of event
            evt = self.buildEventClassKey(evt)
            evt['monitor'] = self.monitor
            if 'summary' in evt:
                evt['summary'] = unicode(evt['summary'] )
            if 'message' in evt:
                evt['message'] = unicode(evt['message'] )
            else: 
                evt['message'] = unicode(msg)
            self.sendEvent(evt)


    def parsePRI(self, evt, msg):
        """
        Parse RFC-3164 PRI part of syslog message to get facility and priority.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @param msg: message from host
        @type msg: string
        @return: tuple of dictionary of event properties and the message
        @type: (dictionary, string)
        """
        pri = self.defaultPriority
        fac = None
        if msg[:1] == '<':
            pos = msg.find('>')
            fac, pri = LOG_UNPACK(int(msg[1:pos]))
            msg = msg[pos+1:]
        elif msg and msg[0] < ' ':
            fac, pri = LOG_KERN, ord(msg[0])
            msg = msg[1:]
        evt['facility'] = fac
        evt['priority'] = pri
        evt['severity'] = self.defaultSeverityMap(pri)
        slog.debug("fac=%s pri=%s", fac, pri)
        slog.debug("facility=%s severity=%s", evt['facility'], evt['severity'])
        return evt, msg


    def defaultSeverityMap(self, pri):
        """
        Default mapping from syslog priority to severity.

        @param pri: syslog priority from host
        @type pri: integer
        @return: numeric severity
        @type: integer
        """
        sev = 1
        if pri < 3: sev = 5
        elif pri == 3: sev = 4
        elif pri == 4: sev = 3
        elif pri == 5 or pri == 6: sev = 2
        return sev


    timeParse = \
        re.compile("^(\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[\d ]{2}(?:\.\d{1,3})?) (.*)", re.DOTALL).search
    notHostSearch = re.compile("[\[:]").search
    def parseHEADER(self, evt, msg):
        """
        Parse RFC-3164 HEADER part of syslog message.  TIMESTAMP format is:
        MMM HH:MM:SS and host is next token without the characters '[' or ':'.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @param msg: message from host
        @type msg: string
        @return: tuple of dictionary of event properties and the message
        @type: (dictionary, string)
        """
        slog.debug(msg)
        m = re.sub("Kiwi_Syslog_Daemon \d+: \d+: "
            "\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[^:]+: ", "", msg)
        m = self.timeParse(msg)
        if m:
            slog.debug("parseHEADER timestamp=%s", m.group(1))
            evt['originalTime'] = m.group(1)
            msg = m.group(2).strip()
        msglist = msg.split()
        if self.parsehost and not self.notHostSearch(msglist[0]):
            device = msglist[0]
            if device.find('@') >= 0:
                device = device.split('@', 1)[1]
            slog.debug("parseHEADER hostname=%s", evt['device'])
            msg = " ".join(msglist[1:])
            evt['device'] = device
            if isip(device):
                evt['ipAddress'] = device
            else:
                if 'ipAddress' in evt:
                    del(evt['ipAddress'])
        return evt, msg


    def parseTag(self, evt, msg):
        """
        Parse the RFC-3164 tag of the syslog message using the regex defined
        at the top of this module.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @param msg: message from host
        @type msg: string
        @return: dictionary of event properties
        @type: dictionary
        """
        slog.debug(msg)
        for parser, keepEntry in compiledParsers:
            slog.debug("tag regex: %s", parser.pattern)
            m = parser.search(msg)
            if not m:
                continue
            elif not keepEntry:
                slog.debug("Dropping syslog message due to parser rule.")
                return None
            slog.debug("tag match: %s", m.groupdict())
            evt.update(m.groupdict())
            break
        else:
            slog.debug("No matching parser: '%s'", msg)
            evt['summary'] = msg
        return evt


    def buildEventClassKey(self, evt):
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
        if 'eventClassKey' in evt or 'eventClass' in evt:
            return evt
        elif 'ntevid' in evt:
            evt['eventClassKey'] = "%s_%s" % (evt['component'],evt['ntevid'])
        elif 'component' in evt:
            evt['eventClassKey'] = evt['component']
        if 'eventClassKey' in evt:
            slog.debug("eventClassKey=%s", evt['eventClassKey'])
            try:
                evt['eventClassKey'] = evt['eventClassKey'].decode('latin-1')
            except Exception:
                evt['eventClassKey'] = evt['eventClassKey'].decode('utf-8')
        else:
            slog.debug("No eventClassKey assigned")
        return evt
