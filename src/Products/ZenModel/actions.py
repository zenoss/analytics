##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from collections import defaultdict
import os
import re
from time import strftime, localtime
import time
import socket
import logging
from socket import getaddrinfo
from traceback import format_exc
from zope.interface import implements
from zope.component import getUtilitiesFor

from pynetsnmp import netsnmp

from twisted.internet.protocol import ProcessProtocol

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate

from zope.tales.tales import CompilerError

from zenoss.protocols.protobufs import zep_pb2
from Products.ZenEvents.events2.proxy import EventSummaryProxy
from Products.ZenUtils.Utils import sendEmail
from Products.Zuul.interfaces.actions import (
    IEmailActionContentInfo, IPageActionContentInfo,
    ICommandActionContentInfo, ISnmpTrapActionContentInfo,
    ISyslogActionContentInfo, ISNMPv3ActionContentInfo
)
from Products.Zuul.form.interfaces import IFormBuilder
from Products.ZenModel.UserSettings import GroupSettings
from Products.ZenModel.interfaces import (
    IAction, IProvidesEmailAddresses, IProvidesPagerAddresses,
    IProcessSignal, INotificationContextProvider,
)
from Products.ZenModel.NotificationSubscription import NotificationEventContextWrapper
from Products.ZenEvents.Event import Event
from Products.ZenUtils import Utils
from Products.ZenUtils.IpUtil import getHostByName, isip
from Products.ZenUtils.guid.guid import GUIDManager
from Products.ZenUtils.ProcessQueue import ProcessQueue
from Products.ZenUtils.ZenTales import talEval, InvalidTalesException
from Products.ZenUtils.Time import convertTimestampToTimeZone, isoToTimestamp
from zenoss.protocols.protobufs.zep_pb2 import (
    SEVERITY_CLEAR, SEVERITY_INFO, SEVERITY_DEBUG,
    SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL,
)

log = logging.getLogger("zen.actions")


class ActionExecutionException(Exception): pass

class TalesMissingZenossDevice(ActionExecutionException): pass

class BadTalesExpresssion(ActionExecutionException): pass


class ActionMissingException(Exception): pass


class TargetableActionException(ActionExecutionException):
    def __init__(self, action, notification, exceptionTargets):
        self.action = action
        self.notificationId = notification.id
        self.exceptionTargets = exceptionTargets
    def __str__(self):
        return "Failed {action} for notification {notification} on targets {targets}".format(
            action=self.action.name,
            notification=self.notificationId,
            targets = ','.join(self.exceptionTargets)
        )

DEVICE_TAL = re.compile('\$\{dev[ice]*/([-A-Za-z_.0-9]+)\}')
NO_ZEN_DEVICE = 'Unable to perform TALES evaluation on "%s" -- no Zenoss device'
BAD_TALES = 'Unable to perform TALES evaluation on "%s"'
def processTalSource(source, skipfails=False, **kwargs):
    """
    This function is used to parse fields made available to actions that allow
    for TAL expressions.
    """
    if not kwargs.get('dev'):
        hasDevReference = re.search(DEVICE_TAL, source)
        if hasDevReference:
            attributes = hasDevReference.groups()
            log.error("The TALES string '%s' references ${dev/xxx} %s,"
                          " but no Zenoss device exists (use ${evt/xxx} fields instead?)",
                          source, attributes)
            message = NO_ZEN_DEVICE % source
            raise TalesMissingZenossDevice(message)

    try:
        context = kwargs.get('here')
        return talEval(source, context, kwargs, skipfails)
    except CompilerError as ex:
        message = "%s: %s" % (ex, source)
        log.error("%s context = %s data = %s", message, context, kwargs)
        raise BadTalesExpresssion(message)
    except InvalidTalesException:
        message = BAD_TALES % source
        log.error("%s context = %s data = %s", message, context, kwargs)
        raise BadTalesExpresssion(message)


def _signalToContextDict(signal, zopeurl, notification=None, guidManager=None):
    summary = signal.event
    # build basic event context wrapper for notifications
    if signal.clear:
        # aged and closed events have clear == True, but they don't have an associated clear event
        #   spoof a clear event in those cases, so the notification messages contain useful info
        if summary.status == zep_pb2.STATUS_AGED:
            occur = signal.clear_event.occurrence.add()
            occur.summary = "Event aging task aged out the event."
            summary.cleared_by_event_uuid = "Event aging task"
        elif summary.status == zep_pb2.STATUS_CLOSED:
            occur = signal.clear_event.occurrence.add()

            # once an event is in a closed state, the ownerid (current_user_name) is removed
            # determine who closed the event by extracting the most recent user_name in the event's audit_log
            last_audit_entry = max(signal.event.audit_log, key=lambda x:x.timestamp)
            summary.current_user_name = last_audit_entry.user_name

            occur.summary = "User '" + summary.current_user_name + "' closed the event in the Zenoss event console."
            summary.cleared_by_event_uuid = "User action"
        data = NotificationEventContextWrapper(summary, signal.clear_event)
    else:
        data = NotificationEventContextWrapper(summary)

    # add urls to event context
    data['urls']['eventUrl'] = getEventUrl(zopeurl, summary.uuid)
    data['urls']['ackUrl'] = getAckUrl(zopeurl, summary.uuid)
    data['urls']['closeUrl'] = getCloseUrl(zopeurl, summary.uuid)
    proxy = EventSummaryProxy(summary)
    data['urls']['deviceUrl'] = _getBaseDeviceUrl(zopeurl, proxy.DeviceClass, proxy.device)
    data['urls']['eventsUrl'] = getEventsUrl(zopeurl, proxy.DeviceClass, proxy.device)
    data['urls']['reopenUrl'] = getReopenUrl(zopeurl, summary.uuid)
    data['urls']['baseUrl'] = zopeurl
    # now process all custom processors that might be registered to enhance
    # the event context
    for key, processor in getUtilitiesFor(IProcessSignal):
        data[key] = processor.process(signal)

    # Process INotificationContextProvider
    for key, contextProvider in getUtilitiesFor(INotificationContextProvider):
        contextProvider.updateContext(signal, data)

    # Add trigger and notification info
    if notification:
        data['notification']['name'] = notification.titleOrId()
    if guidManager:
        trigger = guidManager.getObject(signal.trigger_uuid)
        if trigger:
            data['trigger']['name'] = trigger.titleOrId()

    return data


def _getBaseUrl(zopeurl):
    if not zopeurl:
        zopeurl = Utils.getDefaultZopeUrl()
    return '%s/zport/dmd' % zopeurl


def _getBaseEventUrl(zopeurl):
    return '%s/Events' % _getBaseUrl(zopeurl)


def _getBaseDeviceUrl(zopeurl, device_class, device_name):
    """
    Builds the URL for a device.
    Example: "http://.../Devices/Server/Linux/devices/localhost/devicedetail"
    """
    if device_class and device_name:
        # the device
        return '%s/Devices%s/devices/%s/devicedetail' % \
               (_getBaseUrl(zopeurl), device_class, device_name)
    else:
        # unknown device, just link to infrastructure page
        return "%s/itinfrastructure" % _getBaseUrl(zopeurl)


def getEventUrl(zopeurl, evid):
    return "%s/viewDetail?evid=%s" % (_getBaseEventUrl(zopeurl), evid)


def getEventsUrl(zopeurl, device_class=None, device_name=None):
    if device_class and device_name:
        # events for a specific device
        return "%s#deviceDetailNav:device_events" % _getBaseDeviceUrl(zopeurl, device_class, device_name)
    else:
        #events on all devices
        return "%s/Events/evconsole" % _getBaseUrl(zopeurl)


def getAckUrl(zopeurl, evid):
    return "%s/manage_ackEvents?evids=%s&zenScreenName=viewEvents" %\
           (_getBaseEventUrl(zopeurl), evid)


def getCloseUrl(zopeurl, evid):
    return "%s/manage_deleteEvents?evids=%s&zenScreenName=viewHistoryEvents" %\
           (_getBaseEventUrl(zopeurl), evid)


def getReopenUrl(zopeurl, evid):
    return "%s/manage_undeleteEvents?evids=%s&zenScreenName=viewEvents" %\
           (_getBaseEventUrl(zopeurl), evid)


class IActionBase(object):
    """
    Mixin class for provided some common, necessary, methods.
    """

    def configure(self, options):
        self.options = options

    def getInfo(self, notification):
        return self.actionContentInfo(notification)

    def generateJavascriptContent(self, notification):
        content = self.getInfo(notification)
        return IFormBuilder(content).render(fieldsets=False)

    def getDefaultData(self, dmd):
        return {}

    def updateContent(self, content=None, data=None):
        """
        Use the action's interface definition to grab the content pane
        information data and populate the content object.
        """
        updates = dict()

        for k in self.actionContentInfo.names(all=True):
            if data.get(k) is not None:
                updates[k] = data[k]

        content.update(updates)

    def _signalToContextDict(self, signal, notification=None):
        """
        Parse the event data out from the signal
        """
        # use zopeurl in the zenactiond.conf file if it is defined else use the value from DMD
        zopeurl = self.options.get('zopeurl')
        if zopeurl == Utils.getDefaultZopeUrl() and hasattr(self, "zenossHostname"):
            zopeurl = self.zenossHostname

        data = _signalToContextDict(signal, zopeurl, notification, self.guidManager)
        return data


class TargetableAction(object):
    """
    Mixin class for actions that use user information
    """

    shouldExecuteInBatch = False

    def setupAction(self, dmd):
        """
        Some actions need to configure themselves with properties from the dmd.
        This is their opportunity to do so.
        """
        pass

    def getTargets(self, notification, signal = None):
        targets = set()
        for recipient in notification.recipients:
            if recipient['type'] in ['group', 'user']:
                guid = recipient['value']
                target_obj = self.guidManager.getObject(guid)
                if target_obj:
                    for target in self.getActionableTargets(target_obj):
                        targets.add(target)
            else:
                targets.add(recipient['value'])
        return targets

    def handleExecuteError(self, exception, notification, target):
        # If there is an error executing this action on a target,
        # we need to handle it, but we don't want to prevent other
        # actions from executing on any other targets that may be
        # about to be acted on.
        msg = 'Error executing action {notification} on {target}'.format(
            notification=notification.id,
            target=target,
        )
        log.error(exception)
        log.error(msg)
        traceback = format_exc()
        event = Event(device="localhost",
                      eventClass="/App/Failed",
                      summary=msg,
                      message=traceback,
                      severity=SEVERITY_WARNING, component="zenactiond")
        notification.dmd.ZenEventManager.sendEvent(event)

    def executeBatch(self, notification, signal, targets):
        raise NotImplemented()

    def execute(self, notification, signal):
        self.setupAction(notification.dmd)

        exceptionTargets = []
        targets = self.getTargets(notification, signal)
        if targets:
            if self.shouldExecuteInBatch:
                try:
                    log.debug("Executing batch action for targets.")
                    self.executeBatch(notification, signal, targets)
                except Exception as e:
                    self.handleExecuteError(e, notification, targets)
                    exceptionTargets.extend(targets)
            else:
                log.debug("Executing action serially for targets.")
                for target in targets:
                    try:
                        self.executeOnTarget(notification, signal, target)
                        log.debug('Done executing action for target: %s', target)
                    except Exception as e:
                        self.handleExecuteError(e, notification, target)
                        exceptionTargets.append(target)

            if exceptionTargets:
                raise TargetableActionException(self, notification, exceptionTargets)
        else:
            log.debug("No action executed because no targets were found")


class EmailAction(IActionBase, TargetableAction):
    implements(IAction)
    id = 'email'
    name = 'Email'
    actionContentInfo = IEmailActionContentInfo

    shouldExecuteInBatch = True

    def __init__(self):
        super(EmailAction, self).__init__()

    def configure(self, options):
        super(EmailAction, self).configure(options)
        self.stripBodyTags = options.get('stripEmailBodyTags', True)

    def getDefaultData(self, dmd):
        return dict(host=dmd.smtpHost,
                    port=dmd.smtpPort,
                    user=dmd.smtpUser,
                    password=dmd.smtpPass,
                    useTls=dmd.smtpUseTLS,
                    email_from=dmd.getEmailFrom())

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.zenossHostname = dmd.zenossHostname

    def _get_recipients_from_signal(self, notification, signal):
        ''' Check for any recipients passed in the event details '''
        raw_recipients = self._signalToContextDict(signal, notification)['evt'].details.get('recipients', '')
        recipients = [ recipient.strip() for recipient in raw_recipients.split(',') if recipient.strip() ]
        return set(recipients)

    def getTargets(self, notification, signal = None):

        targets = super(EmailAction, self).getTargets(notification)

        if signal:
            signal_targets = self._get_recipients_from_signal(notification, signal)
            if signal_targets:
                log.debug('Adding recipients found in the event details: %s', ','.join(signal_targets))
                targets = targets.union(signal_targets)
        return targets

    def _encodeBody(self, body):
        """
        Try to encode the text in the following character sets, if we can't decode it
        then strip out anything we can't encode in ascii.
        """
        for body_charset in 'US-ASCII', 'UTF-8':
            try:
                plain_body = MIMEText(body.encode(body_charset), 'plain', body_charset)
                break
            except UnicodeError:
                pass
        else:
            plain_body = MIMEText(body.decode('ascii', 'ignore'))
        return plain_body

    def _targetsByTz(self, dmd, targets):
        """
        Take timezone from user property to convert a event time in
        notification and also group targets emails by those timezones.
        """
        tz_targets = {}
        targetsCopy = set(targets)
        for user in dmd.ZenUsers.getAllUserSettings():
            if user.email in targets:
                tz_targets.setdefault(user.timezone, set()).add(user.email)
                targetsCopy.discard(user.email)
        if targetsCopy: #some emails are not from users in the system
            tz = time.tzname[time.daylight] # get current timezone factoring in daylight saving
            tz_targets.setdefault(tz, set()).update(targetsCopy)
        return tz_targets

    def _adjustToTimezone(self, millis, timezone):
        """
        Convert event timestamp to timezone from user property.
        """
        return long(isoToTimestamp(convertTimestampToTimeZone(
                    millis / 1000, timezone, "%Y-%m-%d %H:%M:%S"
                    ))) * 1000

    def executeBatch(self, notification, signal, targets):
        log.debug("Executing %s action for targets: %s", self.name, targets)
        self.setupAction(notification.dmd)
        tz_targets = self._targetsByTz(notification.dmd, targets)
        original_lst = signal.event.last_seen_time
        original_fst = signal.event.first_seen_time
        original_sct = signal.event.status_change_time
        for target_timezone, targets in tz_targets.iteritems():
            num_of_attempts = 3
            for attempt in xrange(1, num_of_attempts+1):
                # Convert timestamp to user timezone
                signal.event.last_seen_time = self._adjustToTimezone(
                    original_lst, target_timezone)
                signal.event.first_seen_time = self._adjustToTimezone(
                    original_fst, target_timezone)
                signal.event.status_change_time =  self._adjustToTimezone(
                    original_sct, target_timezone)

                data = self._signalToContextDict(signal, notification)

                # Check for email recipients in the event
                details = data['evt'].details
                mail_targets = details.get('recipients', '')
                mail_targets = [x.strip() for x in mail_targets.split(',') if x.strip()]
                if len(mail_targets) > 0:
                    log.debug("Adding recipients defined in the event %s", mail_targets)
                    targets |= set(mail_targets)

                skipfails = notification.content.get('skipfails', False)

                if signal.clear:
                    log.debug("Generating a notification at enabled 'Send Clear' option when event was closed")
                    subject = processTalSource(notification.content['clear_subject_format'], skipfails, **data)
                    body = processTalSource(notification.content['clear_body_format'], skipfails, **data)
                else:
                    subject = processTalSource(notification.content['subject_format'], skipfails, **data)
                    body = processTalSource(notification.content['body_format'], skipfails, **data)

                log.debug('Sending this subject: %s', subject)

                # Find all time strings in body and add timezone to it
                body = re.sub(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3})',
                              r'\1 ({})'.format(target_timezone), body)

                plain_body = self._encodeBody(self._stripTags(body)) \
                    if self.stripBodyTags else self._encodeBody(body)

                email_message = plain_body

                if notification.content['body_content_type'] == 'html':
                    email_message = MIMEMultipart('related')
                    email_message_alternative = MIMEMultipart('alternative')
                    email_message_alternative.attach(plain_body)
                    html_body = self._encodeBody(body)
                    html_body.set_type('text/html')
                    email_message_alternative.attach(html_body)

                    email_message.attach(email_message_alternative)
                    log.debug('Sending this body: %s', body)
                else:
                    log.debug('Sending this body: %s', plain_body)

                host = notification.content['host']
                port = notification.content['port']
                user = notification.content['user']
                password = notification.content['password']
                useTls = notification.content['useTls']
                email_from = notification.content['email_from']

                email_message['Subject'] = subject
                email_message['From'] = email_from
                email_message['To'] = ','.join(targets)
                email_message['Date'] = formatdate(None, True)

                result, errorMsg = sendEmail(
                    email_message,
                    host, port,
                    useTls,
                    user, password
                )

                if result:
                    log.debug("Notification '%s' sent emails to: %s",
                             notification.id, targets)
                elif "socket.error" in errorMsg:
                    if attempt < num_of_attempts:
                        current_timeout = attempt * 5
                    log.info('socket.error: %s. Still have time to try again. Try in %d seconds again...' %
                             (errorMsg, current_timeout))
                    time.sleep(current_timeout)
                    continue
                else:
                    raise ActionExecutionException(
                        "Notification '%s' FAILED to send emails to %s: %s" %
                        (notification.id, targets, errorMsg)
                    )

    def getActionableTargets(self, target):
        """
        @param target: This is an object that implements the IProvidesEmailAddresses
            interface.
        @type target: UserSettings or GroupSettings.
        """
        if IProvidesEmailAddresses.providedBy(target):
            return target.getEmailAddresses()

    def _stripTags(self, data):
        """A quick html => plaintext converter
           that retains and displays anchor hrefs

           stolen from the old zenactions.
           @todo: needs to be updated for the new data structure?
        """
        tags = re.compile(r'<(.|\n)+?>', re.I | re.M)
        aattrs = re.compile(r'<a(.|\n)+?href=["\']([^"\']*)[^>]*?>([^<>]*?)</a>', re.I | re.M)
        anchors = re.finditer(aattrs, data)
        for x in anchors: data = data.replace(x.group(), "%s: %s" % (x.groups()[2], x.groups()[1]))
        data = re.sub(tags, '', data)
        return data


class PageAction(IActionBase, TargetableAction):
    implements(IAction)

    id = 'page'
    name = 'Page'
    actionContentInfo = IPageActionContentInfo
    shouldExecuteInBatch = False

    def configure(self, options):
        super(PageAction, self).configure(options)
        self.pagingWorkersTimeout = options.get('pagingWorkersTimeout', 30)
        self.processQueue = ProcessQueue(options.get('maxPagingWorkers', 1))
        self.processQueue.start()

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.dmd = dmd
        self.page_command = dmd.pageCommand
        self.zenossHostname = dmd.zenossHostname

    def executeOnTarget(self, notification, signal, target):
        log.debug('Executing Page %s action on %s', self.name, target)
        environ = dict(os.environ)
        environ["RECIPIENT"] = target
        self._execute(notification, signal, environ)

    def _execute(self, notification, signal, env={}):
        self.setupAction(notification.dmd)
        log.debug('Executing page action: %s', self.name)
        data = self._signalToContextDict(signal, notification)

        skipfails = notification.content.get('skipfails', False)

        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = processTalSource(notification.content['clear_subject_format'], skipfails, **data)
        else:
            subject = processTalSource(notification.content['subject_format'], skipfails, **data)

        msg = str(subject)

        log.debug('Sending page message: "%s"', msg)
        _protocol = SendPageProtocol(msg, notification)
        log.debug('Queueing up page action process. Page command is %s', self.page_command)
        self.processQueue.queueProcess(
            '/bin/sh', ('/bin/sh', '-c', self.page_command),
            env=env,
            processProtocol=_protocol,
            timeout=self.pagingWorkersTimeout,
            timeout_callback=_protocol.timedOut
        )

    def getActionableTargets(self, target):
        """
        @param target: This is an object that implements the IProvidesPagerAddresses
            interface.
        @type target: UserSettings or GroupSettings.
        """
        if IProvidesPagerAddresses.providedBy(target):
            return target.getPagerAddresses()


class EventCommandProtocol(ProcessProtocol):
    def __init__(self, cmd, notification):
        self.cmd = cmd
        self.notification = notification
        self.data = ''
        self.error = ''

    def timedOut(self, reason):
        message = "Notification command %s timed out -- %s: stdout: %s\nstderr: %s" % (
                  self.notification.titleOrId(), self.data, self.error)
        log.error(message)
        log.error("Command executed: %s", self.cmd)
        self.sendEvent(reason, "Command timed out", message, SEVERITY_ERROR)
        return reason

    def processEnded(self, reason):
        code = reason.value.exitCode
        if code == 0:
            message = "Command %s finished successfully (exit code 0) with the following output: %s %s" % (
                     self.notification.titleOrId(), self.data, self.error)
            log.info(message)
            log.debug("Command executed: %s", self.cmd)
            self.sendEvent(reason, "Command failed", message, SEVERITY_CLEAR)
        else:
            message = "Command %s failed (exit code %s) -- %s: stdout: %s\nstderr: %s" % (
                      self.notification.titleOrId(), reason.getErrorMessage(), code, self.data, self.error)
            log.error(message)
            log.error("Command executed: %s", self.cmd)
            self.sendEvent(reason, "Command failed", message, SEVERITY_ERROR)

    def outReceived(self, text):
        self.data += text

    def errReceived(self, text):
        self.error += text

    def sendEvent(self, reason, summary, message, severity):
        eventKey= '_'.join([self.notification.action, self.notification.id])
        event = Event(device="localhost",
                      eventClass="/Cmd/Failed",
                      summary="%s %s" % (self.notification.id, summary),
                      message=message,
                      eventKey=eventKey,
                      notification=self.notification.titleOrId(),
                      stdout=self.data,
                      stderr=self.error,
                      severity=severity,
                      component="zenactiond")
        self.notification.dmd.ZenEventManager.sendEvent(event)

class SendPageProtocol(ProcessProtocol):
    def __init__(self, msg, notification):
        self.notification = notification
        self.msg = msg
        self.out = ''
        self.err = ''

    def connectionMade(self):
        log.debug("Writing to subproccess stdin")
        self.transport.write(self.msg)
        self.transport.closeStdin()

    def outReceived(self, data):
        self.out += data

    def errReceived(self, data):
        self.err += data

    def timedOut(self, reason):
        message = "Paging command %s timed out -- %s: stdout: %s\nstderr: %s" % (
                  self.notification.titleOrId(), self.out, self.err)
        log.error(message)
        self.sendEvent(reason, "Paging command timed out", message, SEVERITY_ERROR)
        return reason

    def processEnded(self, reason):
        code = reason.value.exitCode
        if code == 0:
            message = "Paging message sent successfully (exit code 0) with the following output: %s %s" % (
                     self.out, self.err)
            log.info(message)
            self.sendEvent(reason, "Paging failed", message, SEVERITY_CLEAR)
        else:
            message = "Failed to send paging message \"%s\" (exit code %s) -- %s: stdout: %s\nstderr: %s" % (
                      self.msg, reason.getErrorMessage(), code, self.out, self.err)
            log.error(message)
            self.sendEvent(reason, "Paging command failed", message, SEVERITY_ERROR)

    def sendEvent(self, reason, summary, message, severity):
        eventKey = '_'.join([self.notification.action, self.notification.id])
        event = Event(device="localhost",
                      eventClass="/Cmd/Failed",
                      summary="%s %s" % (self.notification.id, summary),
                      message=message,
                      eventKey=eventKey,
                      notification=self.notification.titleOrId(),
                      stdout=self.out,
                      stderr=self.err,
                      severity=severity,
                      component="zenactiond")
        self.notification.dmd.ZenEventManager.sendEvent(event)


class CommandAction(IActionBase, TargetableAction):
    implements(IAction)

    id = 'command'
    name = 'Command'
    actionContentInfo = ICommandActionContentInfo

    shouldExecuteInBatch = False

    def configure(self, options):
        super(CommandAction, self).configure(options)
        self.processQueue = ProcessQueue(options.get('maxCommands', 10))
        self.processQueue.start()

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.dmd = dmd
        self.zenossHostname = dmd.zenossHostname

    def execute(self, notification, signal):
        # check to see if we have any targets
        if notification.recipients:
            return super(CommandAction, self).execute(notification, signal)
        else:
            self._execute(notification, signal)

    def executeOnTarget(self, notification, signal, target):
        log.debug('Executing command action: %s on %s', self.name, target)
        environ = {}
        environ['user'] = getattr(self.dmd.ZenUsers, target, None)
        self._execute(notification, signal, environ)

    def _execute(self, notification, signal, extra_env= {}):
        self.setupAction(notification.dmd)
        log.debug('Executing command action: %s', self.name)

        if signal.clear:
            command = notification.content['clear_body_format']
        else:
            command = notification.content['body_format']

        log.debug('Executing this command: %s', command)

        actor = signal.event.occurrence[0].actor
        device = None
        if actor.element_uuid:
            device = self.guidManager.getObject(actor.element_uuid)

        component = None
        if actor.element_sub_uuid:
            component = self.guidManager.getObject(actor.element_sub_uuid)

        user_env_format = notification.content.get('user_env_format', '') or ''
        env = os.environ.copy()
        user_env = dict( envvar.split('=', 1) for envvar in user_env_format.split(';') if '=' in envvar)
        env.update(user_env)
        environ = {'dev': device, 'component': component, 'dmd': notification.dmd, 'env': env}
        data = self._signalToContextDict(signal, notification)
        environ.update(data)

        if environ.get('evt', None):
            environ['evt'] = self._escapeEvent(environ['evt'])
        if environ.get('clearEvt', None):
            environ['clearEvt'] = self._escapeEvent(environ['clearEvt'])
        environ.update(extra_env)

        # Get the proper command
        command = processTalSource(command, **environ)

        log.debug('Executing this compiled command: "%s"', command)
        _protocol = EventCommandProtocol(command, notification)

        log.debug('Queueing up command action process.')
        self.processQueue.queueProcess(
            '/bin/sh',
                ('/bin/sh', '-c', command),
            env=environ['env'],
            processProtocol=_protocol,
            timeout=int(notification.content['action_timeout']),
            timeout_callback=_protocol.timedOut
        )

    def getActionableTargets(self, target):
        ids = [target.id]
        if isinstance(target, GroupSettings):
            ids = [x.id for x in target.getMemberUserSettings()]
        return ids

    def _escapeEvent(self, evt):
        """
        Escapes the relavent fields of an event context for event commands.
        """
        if evt.message:
            evt.message = self._wrapInQuotes(evt.message)
        if evt.summary:
            evt.summary = self._wrapInQuotes(evt.summary)
        return evt

    def _wrapInQuotes(self, msg):
        """
        Wraps the message in quotes, escaping any existing quote.

        Before:  How do you pronounce "Zenoss"?
        After:  "How do you pronounce \"Zenoss\"?"
        """
        QUOTE = '"'
        BACKSLASH = '\\'
        return ''.join((QUOTE, msg.replace(QUOTE, BACKSLASH + QUOTE), QUOTE))


class SNMPTrapAction(IActionBase):
    implements(IAction)

    id = 'trap'
    name = 'SNMP Trap (v1/v2c)'
    actionContentInfo = ISnmpTrapActionContentInfo

    _sessions = defaultdict(dict)

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.zenossHostname = dmd.zenossHostname

    def execute(self, notification, signal):
        """
        Send out an SNMP trap according to the definition in ZENOSS-MIB.
        """
        log.debug('Processing SNMP Trap action.')
        self.setupAction(notification.dmd)
        data = self._signalToContextDict(signal, notification)

        # For clear signals we need to send the "clear" event first so the
        # receiver will be able to correlate the later "cleared" event's
        # evtClearId value.

        # Only send the "clear" event if it has a uuid. A clear signal will be
        # sent if a user closing an event, or if it's automatically aged.
        if signal.clear and data['clearEventSummary'].uuid:
            self._sendTrap(notification, data, data['clearEventSummary'])

        self._sendTrap(notification, data, data['eventSummary'])

    def _sendTrap(self, notification, data, event):
        actor = getattr(event, "actor", None)
        details = event.details
        baseOID = '1.3.6.1.4.1.14296.1.100'

        fields = {
           'uuid' :                         ( 1, event),
           'fingerprint' :                  ( 2, event),
           'element_identifier' :           ( 3, actor),
           'element_sub_identifier' :       ( 4, actor),
           'event_class' :                  ( 5, event),
           'event_key' :                    ( 6, event),
           'summary' :                      ( 7, event),
           'message' :                      ( 8, event),
           'severity' :                     ( 9, event),
           'status' :                       (10, event),
           'event_class_key' :              (11, event),
           'event_group' :                  (12, event),
           'state_change_time' :            (13, event),
           'first_seen_time' :              (14, event),
           'last_seen_time' :               (15, event),
           'count' :                        (16, event),
           'zenoss.device.production_state':(17, details),
           'agent':                         (20, event),
           'zenoss.device.device_class':    (21, details),
           'zenoss.device.location' :       (22, details),
           'zenoss.device.systems' :        (23, details),
           'zenoss.device.groups' :         (24, details),
           'zenoss.device.ip_address':      (25, details),
           'syslog_facility' :              (26, event),
           'syslog_priority' :              (27, event),
           'nt_event_code' :                (28, event),
           'current_user_name' :            (29, event),
           'cleared_by_event_uuid' :        (31, event),
           'zenoss.device.priority' :       (32, details),
           'event_class_mapping_uuid':      (33, event),
           'element_title':                 (34, actor),
           'element_sub_title':             (35, actor)
           }

        eventDict = self.createEventDict(fields, event)
        self.processEventDict(eventDict, data, notification.dmd)
        varbinds = self.makeVarBinds(baseOID, fields, eventDict)

        session = self._getSession(notification.content)

        for v in varbinds:
            log.debug(v)
        session.sendTrap(baseOID + '.0.0.1', varbinds=varbinds)

    def createEventDict(self, fields, event):
        """
        Create an event dictionary suitable for Python evaluation.
        """
        eventDict = {}
        for field, oidspec in fields.items():
            i, source = oidspec
            if source is event.details:
                val = source.get(field, '')
            else:
                val = getattr(source, field, '')
            eventDict[field] = val
        return eventDict

    def processEventDict(self, eventDict, data, dmd):
        """
        Integration hook
        """
        pass

    def makeVarBinds(self, baseOID, fields, eventDict):
        """
        Make the SNMP variable bindings in numeric order.
        """
        uintValues = (9, 10, 26, 27)
        varbinds = []
        for field, oidspec in sorted(fields.items(), key=lambda x: x[1][0]):
            i, source = oidspec
            val = eventDict.get(field, '')
            if isinstance(val, (list, tuple, set)):
                val = '|'.join(val)

            # Create the binding
            oid = "%s.%d" % (baseOID, i)
            oidType = 's' if i not in uintValues else 'u'
            # No matter what the OID data type, send in strings as that's what is expected
            val = str(val)

            varbinds.append( (oid, oidType, val) )
        return varbinds

    def _getSession(self, content):
        traphost = content['action_destination']
        port = content.get('port', 162)
        destination = '%s:%s' % (traphost, port)

        if not traphost or port <= 0:
            log.error("%s: SNMP trap host information %s is incorrect ", destination)
            return None

        community = content.get('community', 'public')
        version = content.get('version', 'v2c')

        session = self._sessions[destination].get(version, None)
        if session is None:
            log.debug("Creating SNMP trap session to %s", destination)

            # Test that the hostname and port are sane.
            try:
                getaddrinfo(traphost, port)
            except Exception:
                raise ActionExecutionException("The destination %s is not resolvable." % destination)

            session = netsnmp.Session((
                '-%s' % version,
                '-c', community,
                destination)
            )
            agent_addr = os.getenv('CONTROLPLANE_HOST_IPS', '').split(' ')[0]
            if agent_addr:
                session.agent_addr = agent_addr
            session.open()
            self._sessions[destination][version] = session

        return session


class SNMPv3Action(SNMPTrapAction):
    id = "snmpv3_trap"
    name = "SNMP Trap (v3)"
    actionContentInfo = ISNMPv3ActionContentInfo

    def _getSession(self, content):
        """
        Override to build an SNMPv3 Session
        """

        ###
        # Get configs

        traphost = content['action_destination']
        port = content.get('port', 162)
        destination = '{}:{}'.format(traphost, port)
        if not traphost or port <= 0:
            log.error("%s: SNMP trap host information %s is incorrect ", destination)
            return None

        contextName = content['contextName']
        securityEngineId = content['securityEngineId']
        contextEngineId = content['contextEngineId']
        securityName = content['securityName']
        securityPassphrase = content['securityPassphrase']
        privacyPassphrase = content['privacyPassphrase']
        authProto = content['authProto'] if content['authProto'] != "None" else None
        privProto = content['privProto'] if content['privProto'] != "None" else None

        version = 'v3'

        usingAuth = False
        usingPriv = False

        ###
        # Build Session

        args = ('-%s' % version, )
        if contextName:
            args += ( '-n', contextName)
        if securityEngineId:
            args += ('-e', securityEngineId)
        if contextEngineId:
            args += ('-E', contextEngineId)
        args += ( '-u', securityName)
        if authProto:
            usingAuth = True
            args += (
                '-a', authProto,
                '-A', securityPassphrase,
            )
        if privProto:
            usingPriv = True
            args += (
                '-x', privProto,
                '-X', privacyPassphrase,
            )
        securityLevel = 'noAuthNoPriv'
        if usingAuth:
            if usingPriv:
                securityLevel = 'authPriv'
            else:
                securityLevel = 'authNoPriv'
        args += (
            '-l', securityLevel,
            destination
        )

        session = netsnmp.Session(args)
        agent_addr = os.getenv('CONTROLPLANE_HOST_IPS', '').split(' ')[0]
        if agent_addr:
            session.agent_addr = agent_addr
        session.open()

        return session


class SyslogAction(IActionBase):
    implements(IAction)

    id = 'syslog'
    name = 'Syslog'
    actionContentInfo = ISyslogActionContentInfo

    _sock = None

    severityToSyslogPriority = {
       SEVERITY_CLEAR:    5, # NOTICE
       SEVERITY_DEBUG:    7, # DEBUG
       SEVERITY_INFO:     2, # INFO
       SEVERITY_WARNING:  4, # WARNING
       SEVERITY_ERROR:    3, # ERROR
       SEVERITY_CRITICAL: 2, # CRITICAL
    }
     # Note: not using syslog priorities:
     #      EMERGENCY 0
     #      ALERT     1
    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.zenossHostname = dmd.zenossHostname

    def execute(self, notification, signal):
        """
        Send out a syslog message
        """
        log.debug('Processing syslog action.')
        self.setupAction(notification.dmd)

        data = self._signalToContextDict(signal, notification)
        event = data['eventSummary']

        # Construct the syslog packet
        facility = self.getFacility(notification.content, event)
        priority = self.getPriority(notification.content, event)
        device = self.getDeviceName(event)

        packet = self._makeSyslogPacket(facility, priority, event.last_seen_time,
                                        device, event.summary)

        # Send the syslog packet
        self._openConnection(notification.id, notification.content)
        try:
            self._sock.sendall(packet)
        except socket.error as ex:
            self._sock.close()
            self._sock = None
            msg = "Notification '%s' FAILED to send syslog messages to %s: %s" % (
                notification.id, (self.ipaddr, self.port, self.protocol), ex)
            log.error(msg)
            raise ActionExecutionException(msg)

    def getFacility(self, content, event):
        return content['facility']

    def getPriority(self, content, event):
        SyslogErrorLevel = 3
        priority = self.severityToSyslogPriority.get(event.severity, SyslogErrorLevel)
        return priority

    def getDeviceName(self, event):
        # See RFC3164:
        #  * The preferred value is the hostname, and fallback to  IP address.
        #  * The Domain Name MUST NOT be included in the HOSTNAME field.
        #    However, lots of clients do it anyway.  Fall back to that field.
        hostname = event.actor.element_title
        if not isip(hostname):
            hostname = hostname.split('.')[0].strip()
        return hostname

    def _openConnection(self, notificationId, content):

        if self._sock is not None:
            return

        host = content['host']
        self.port = int(content['port'])

        self.ipaddr = getHostByName(host)

        # IPv[46]
        AF = socket.AF_INET6 if ':' in self.ipaddr else socket.AF_INET

        # Set the socket type
        self.protocol = content['protocol'].lower()
        ST = socket.SOCK_STREAM if self.protocol == 'tcp' else socket.SOCK_DGRAM

        # Try to connect
        self._sock = socket.socket(AF, ST)
        try:
            self._sock.connect( (self.ipaddr, self.port) )
        except socket.error as ex: # Connection failed
            self._sock.close()
            self._sock = None
            msg = "Notification '%s' FAILED to send syslog messages to %s: %s" % (
                notificationId, (self.ipaddr, self.port, self.protocol), ex)
            log.error(msg)
            raise ActionExecutionException(msg)

    def _makeSyslogPacket(self, facility, priority, dt, host, msg):
        # Force msg to have only ASCII 32-126 (inclusive)
        # See RFC3164 for details
        msg = ''.join([c if ord(c) >= 32 and ord(c) <= 126 else '_' for c in msg])
        msg = msg.strip('_') # Strip off meaningless characters from the ends only

        PRI = int(facility) * 8 + int(priority)
        # divide 'dt' to represent is as seconds
        timestamp = strftime("%b %e %T", localtime(dt/1000))
        return ("<%d>%s %s %s" % (PRI, timestamp, host, msg))[:1023] + "\n"
