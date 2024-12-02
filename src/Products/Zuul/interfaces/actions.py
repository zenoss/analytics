##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from Products.ZenUtils.snmp import authentication_protocols, privacy_protocols
from Products.Zuul.interfaces import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t
from zope.schema.vocabulary import SimpleVocabulary
import textwrap


def getNotificationBodyTypes():
    return ['html', 'text']

class IActionContentInfo(IInfo):
    """
    Base class for all other action content information
    """
    pass


class IEmailActionContentInfo(IActionContentInfo):

    body_content_type = schema.Choice(
        title       = _t(u'Body Content Type'),
        vocabulary  = SimpleVocabulary.fromValues(getNotificationBodyTypes()),
        description = _t(u'The content type of the body for emails.'),
        default     = u'html'
    )

    subject_format = schema.TextLine(
        title       = _t(u'Message (Subject) Format'),
        description = _t(u'The template for the subject for emails.'),
        default     = _t(u'[zenoss] ${evt/device} ${evt/summary}')
    )

    body_format = schema.Text(
        title       = _t(u'Body Format'),
        description = _t(u'The template for the body for emails.'),
        default     = textwrap.dedent(text = u'''
        Device: ${evt/device} <br />
        Component: ${evt/component} <br />
        Severity: ${evt/severity} <br />
        Time: ${evt/lastTime} <br />
        Message: <br />
        ${evt/message} <br />
        <a href="${urls/eventUrl}">Event Detail</a><br />
        <a href="${urls/ackUrl}">Acknowledge</a><br />
        <a href="${urls/closeUrl}">Close</a><br />
        <a href="${urls/eventsUrl}">Device Events</a><br />
        ''')
    )

    clear_subject_format = schema.TextLine(
        title       = _t(u'Clear Message (Subject) Format'),
        description = _t(u'The template for the subject for CLEAR emails.'),
        default     = _t(u'[zenoss] CLEAR: ${evt/device} ${clearEvt/summary}')
    )

    clear_body_format = schema.Text(
        title       = _t(u'Body Format'),
        description = _t(u'The template for the body for CLEAR emails.'),
        default     = textwrap.dedent(text = u'''
        Event: '${evt/summary}' <br />
        Cleared by: '${evt/clearid}' <br />
        At: ${evt/stateChange} <br />
        Device: ${evt/device} <br />
        Component: ${evt/component} <br />
        Severity: ${evt/severity} <br />
        Message: <br />
        ${evt/message} <br />
        <a href="${urls/reopenUrl}">Reopen</a><br />
        ''')
    )

    skipfails = schema.Bool(
        title       = _t(u'Skip fails in TALES evaluation ?'),
        description = _t(u'Skip bad TALES expressions')
    )

    email_from = schema.Text(
        title       = _t(u'From Address for Emails'),
        description = _t(u'The user from which the e-mail originated on the Zenoss server.'),
    )

    host = schema.Text(
        title       = _t(u'SMTP Host'),
        description = _t(u'Simple Mail Transport Protocol (aka E-mail server).'),
    )

    port = schema.Int(
        title       = _t(u'SMTP Port (usually 25)'),
        description = _t(u'TCP/IP port to access Simple Mail Transport Protocol (aka E-mail server).'),
    )

    useTls = schema.Bool(
        title       = _t(u'Use TLS?'),
        description = _t(u'Use Transport Layer Security for E-mail?')
    )

    user = schema.Text(
        title       = _t(u'SMTP Username (blank for none)'),
        description = _t(u'Use this only if authentication is required.'),
    )

    password = schema.Password(
        title       = _t(u'SMTP Password (blank for none)'),
        description = _t(u'Use this only if authentication is required.'),
    )


class IPageActionContentInfo(IActionContentInfo):

    subject_format = schema.TextLine(
        title       = _t(u'Message (Subject) Format'),
        description = _t(u'The template for the subject for pages.'),
        default     = _t(u'[zenoss] ${evt/device} ${evt/summary}')
    )

    clear_subject_format = schema.TextLine(
        title       = _t(u'Clear Message (Subject) Format'),
        description = _t(u'The template for the subject for CLEAR pages.'),
        default     = _t(u'[zenoss] CLEAR: ${evt/device} ${clearEvt/summary}')
    )


class ICommandActionContentInfo(IActionContentInfo):

    action_timeout = schema.Int(
        title       = _t(u'Command Timeout (seconds)'),
        description = _t(u'How long before the command times out.'),
        default     = 60
    )

    body_format = schema.Text(
        title       = _t(u'Command'),
        description = _t(u'The template for the body for commands.')
    )

    clear_body_format = schema.Text(
        title       = _t(u'Clear Command'),
        description = _t(u'The template for the body for CLEAR commands.')
    )

    user_env_format = schema.Text(
        title       = _t(u'Environment variables'),
        description = _t(u'A semi-colon separated list of environment variables.'),
    )


class ISnmpTrapActionContentInfo(IActionContentInfo):

    action_destination = schema.TextLine(
        title       = _t(u'SNMP Trap Destination'),
        description = _t(u'The template for the subject for the SNMP trap destination.'),
        default     = _t(u'traphost')
    )

    community = schema.Text(
        title       = _t(u'SNMP Community'),
        description = _t(u'SNMP authentication string.'),
        default = _t(u'public')
    )

    version = schema.Choice(
        title       = _t(u'SNMP Version'),
        description = _t(u'SNMP trap protocol version.'),
        vocabulary  = SimpleVocabulary.fromValues(['v1', 'v2c']),
        default = _t(u'v2c')
    )

    port = schema.Int(
        title       = _t(u'SNMP Port (usually 162)'),
        description = _t(u'Port number used by the SNMP trap receiver process.'),
        default = 162
    )


class ISNMPv3ActionContentInfo(ISnmpTrapActionContentInfo):
    # hide unused fields
    version = schema.Text(title=_t(u''), xtype="hidden")
    community = schema.Text(title=_t(u''), xtype="hidden")

    securityEngineId = schema.TextLine(
        title=_t(u'Security Engine ID'),
        default=u'0x0102030405'
    )
    contextEngineId = schema.TextLine(
        title=_t(u'Context Engine ID'),
    )

    contextName = schema.TextLine(title=_t(u'Context Name'))

    authProto = schema.Choice(title=_t(u"Authentication Protocol"),
        vocabulary=SimpleVocabulary.fromValues(
            ('None',) + authentication_protocols
        ),
        default=_t(u'None'),
    )
    securityName = schema.TextLine(title=_t(u'Security Name'))
    securityPassphrase = schema.Password(title=_t(u'Security Passphrase'))

    privProto = schema.Choice(title=_t(u"Privacy Protocol"),
        vocabulary=SimpleVocabulary.fromValues(('None',) + privacy_protocols),
        default=_t(u'None'),
    )
    privacyPassphrase = schema.Password(title=_t(u'Privacy Passphrase'))


class ISyslogActionContentInfo(IInfo):
    host = schema.Text(
        title       = _t(u'Syslog Host'),
        description = _t(u'Server hosting the syslog service that can receive syslog messages).'),
    )

    port = schema.Int(
        title       = _t(u'Syslog Port (usually 514)'),
        description = _t(u'TCP/IP port to access syslog.'),
        default = 514
    )

    protocol = schema.Choice(
        title       = _t(u'Protocol'),
        description = _t(u'Syslog protocol.'),
        vocabulary  = SimpleVocabulary.fromValues(['TCP', 'UDP']),
        default = _t(u'UDP')
    )

    facility = schema.Choice(
        title       = _t(u'Syslog Facility'),
        description = _t(u'Outgoing syslog facility name to use.'),
        vocabulary  = SimpleVocabulary.fromItems([
              ('KERN', 0), ('USER', 1), ( 'MAIL',  2), ('DAEMON', 3), ('AUTH', 4),
              ('SYSLOG', 5), ('LPR', 6), ('NEWS', 7), ('UUCP', 8), ('CRON', 9),
              ('AUTHPRIV', 10), ('FTP', 11), ('LOCAL0', 16), ('LOCAL1', 17),
              ('LOCAL2', 18), ('LOCAL3', 19), ('LOCAL4', 20), ('LOCAL5', 21),
              ('LOCAL6', 22), ('LOCAL7', 23),
        ]),
    )   

