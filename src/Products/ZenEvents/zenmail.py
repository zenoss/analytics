##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# Notes: database wants events in UTC time
# Events page shows local time, as determined on the server where zenoss runs

__doc__ = """zenmail

Listen on the SMTP port and convert email messages into events.

To test:
 # Test pre-reqs
 yum -y install mailx sendmail

 # Mail to the local zenmail instance
mail -s "Hello world" bogo@localhost
Happy happy, joy, joy
.
Cc:

"""

import logging
from email.Header import Header
import email
import os
import socket

import zope.interface
import zope.component
from zope.interface import implements

from twisted.mail import smtp
from twisted.internet import reactor, protocol, defer

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences,\
                                             IEventService, \
                                             IScheduledTask
from Products.ZenCollector.tasks import NullTaskSplitter,\
                                        BaseTask, TaskStates

# Invalidation issues arise if we don't import
from Products.ZenCollector.services.config import DeviceProxy

from Products.ZenEvents.MailProcessor import MailProcessor
from Products.ZenUtils.Utils import unused
unused(DeviceProxy)


COLLECTOR_NAME = 'zenmail'
log = logging.getLogger("zen.%s" % COLLECTOR_NAME)


class MailPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new PingCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.NullConfig'

        # Will be filled in based on buildOptions
        self.options = None

        self.configCycleInterval = 20*60

    def postStartupTasks(self):
        task = MailListeningTask(COLLECTOR_NAME, configId=COLLECTOR_NAME)
        yield task

    def buildOptions(self, parser):
        """
        Command-line options to be supported
        """
        SMTP_PORT = 25
        try:
            SMTP_PORT = socket.getservbyname('smtp', 'tcp')
        except socket.error:
            pass

        parser.add_option('--useFileDescriptor',
            dest='useFileDescriptor',
            default=-1,
            type="int",
            help="File descriptor to use for listening")
        parser.add_option('--listenPort',
            dest='listenPort',
            default=SMTP_PORT,
            type="int",
            help="Alternative listen port to use (default %default)")
        parser.add_option('--eventseverity',
            dest='eventseverity',
            default="2",
            type="int",
            help="Severity for events created")
        parser.add_option('--listenip',
            dest='listenip',
            default='0.0.0.0',
            help='IP address to listen on. Default is 0.0.0.0')

    def postStartup(self):
        pass


class ZenossEventPoster(object):
    """
    Implementation of interface definition for messages 
    that can be sent via SMTP.
    """
    implements(smtp.IMessage)

    def __init__(self, processor):
        self.lines = []
        self.processor = processor

    def lineReceived(self, line):
        self.lines.append(line)

    def postEvent(self, messageStr):
        email.message_from_string(messageStr)
        self.processor.process(messageStr)

    def eomReceived(self):
        log.info('Message data completed %s.', self.lines)
        self.lines.append('')
        messageData = '\n'.join(self.lines)

        self.postEvent(messageData)

        return defer.succeed("Received End Of Message marker")

    def connectionLost(self):
        log.info('Connection lost unexpectedly')
        del(self.lines)


class ZenossDelivery(object):
    implements(smtp.IMessageDelivery)

    def __init__(self, processor):
        self.processor = processor

    def receivedHeader(self, helo, unused, ignored):
        myHostname, self.clientIP = helo
        date = smtp.rfc822date()

        headerValue = 'by %s from %s with ESMTP ; %s' % (
            myHostname, self.clientIP, date)
        
        log.info('Relayed (or sent directly) from: %s', self.clientIP)
        
        header = 'Received: %s' % Header(headerValue)
        return header

    def validateTo(self, user):
        log.info('to: %s', user.dest)
        return self.makePoster

    def makePoster(self):
        return ZenossEventPoster(self.processor)

    def validateFrom(self, unused, originAddress):
        log.info("from: %s", originAddress)
        return originAddress
    
    
class SMTPFactory(protocol.ServerFactory):
    def __init__(self, processor):
        self.processor = processor

    def buildProtocol(self, unused):
        delivery = ZenossDelivery(self.processor)
        smtpProtocol = smtp.SMTP(delivery)
        smtpProtocol.factory = self
        return smtpProtocol


class MailListeningTask(BaseTask):
    zope.interface.implements(IScheduledTask)

    def __init__(self, taskName, configId,
                 scheduleIntervalSeconds=3600, taskConfig=None):
        BaseTask.__init__(self, taskName, configId,
                 scheduleIntervalSeconds, taskConfig)
        self.log = log

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds
        self._preferences = taskConfig
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = self._daemon

        self.options = self._daemon.options

        # Allow MailProcessor to work unmodified
        self.sendEvent = self._eventService.sendEvent

        if (self.options.useFileDescriptor < 0 and \
            self.options.listenPort < 1024):
            self._daemon.openPrivilegedPort('--listen',
                '--proto=tcp', '--port=%s:%d' % (
                    self.options.listenip, self.options.listenPort))

        self._daemon.changeUser()
        self.processor = MailProcessor(self, self.options.eventseverity)

        self.factory = SMTPFactory(self.processor)

        log.info("listening on %s:%d",
            self.options.listenip, self.options.listenPort)
        if self.options.useFileDescriptor != -1:
            self.useTcpFileDescriptor(int(self.options.useFileDescriptor),
                                      self.factory)
        else:
            reactor.listenTCP(self.options.listenPort, self.factory,
                interface=self.options.listenip)

    def doTask(self):
        """
        This is a wait-around task since we really are called
        asynchronously.
        """
        return defer.succeed("Waiting for SMTP messages...")

    def useTcpFileDescriptor(self, fd, factory):
        for i in range(19800, 19999):
            try:
                p = reactor.listenTCP(i, factory)
                os.dup2(fd, p.socket.fileno())
                p.socket.listen(p.backlog)
                p.socket.setblocking(False)
                p.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                os.close(fd)
                return p
            except socket.error:
                pass
        raise socket.error("Unable to find an open socket to listen on")

    def cleanup(self):
        pass


class MailDaemon(CollectorDaemon):

    _frameworkFactoryName = "nosip"


if __name__=='__main__':
    myPreferences = MailPreferences()
    myTaskSplitter = NullTaskSplitter()
    daemon = MailDaemon(myPreferences, myTaskSplitter)
    daemon.run()
