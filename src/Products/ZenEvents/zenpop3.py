#! /usr/bin/env python 
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

__doc__ = """zenpop3

Turn email messages obtained from POP3 accounts into events.

"""

import logging
import socket

import zope.interface

from twisted.mail.pop3client import POP3Client
from twisted.internet.ssl import ClientContextFactory
from twisted.internet import reactor, protocol, defer, error

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences,\
                                             IEventService, \
                                             IScheduledTask
from Products.ZenCollector.tasks import NullTaskSplitter,\
                                        BaseTask, TaskStates

# Invalidation issues arise if we don't import
from Products.ZenCollector.services.config import DeviceProxy

from Products.ZenEvents.MailProcessor import POPProcessor


COLLECTOR_NAME = 'zenpop3'
log = logging.getLogger("zen.%s" % COLLECTOR_NAME)


class MailPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        self.collectorName = COLLECTOR_NAME
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        self.configurationService = 'Products.ZenHub.services.NullConfig'

        # Will be filled in based on buildOptions
        self.options = None

        self.configCycleInterval = 20*60

    def postStartupTasks(self):
        task = MailCollectingTask(COLLECTOR_NAME, configId=COLLECTOR_NAME)
        yield task

    def buildOptions(self, parser):
        """
        Command-line options to be supported
        """
        POP3_PORT = 110
        try:
            POP3_PORT = socket.getservbyname('pop3', 'tcp')
        except socket.error:
            pass

        parser.add_option('--usessl',
                               dest='usessl',
                               default=False,
                               action="store_true",
                               help="Use SSL when connecting to POP server")
        parser.add_option('--nodelete',
                               dest='nodelete',
                               default=False,
                               action="store_true",
                               help="Leave messages on POP server")
        parser.add_option('--pophost',
                               dest='pophost',
                               default="pop.zenoss.com",
                               help="POP server from which emails are to be read")
        parser.add_option('--popport',
                               dest='popport',
                               default=POP3_PORT,
                               type="int",
                               help="POP port from which emails are to be read")
        parser.add_option('--popuser',
                               dest='popuser',
                               default="zenoss",
                               help="POP user")
        parser.add_option('--poppass',
                               dest='poppass',
                               default="zenoss",
                               help="POP password")
        parser.add_option('--cycletime',
                               dest='cycletime',
                               type="int",
                               default=60,
                               help="Frequency (in seconds) to poll the POP server")
        parser.add_option('--eventseverity',
                               dest='eventseverity',
                               default="2",
                               type="int",
                               help="Severity for events created")

    def postStartup(self):
        pass


class POPProtocol(POP3Client):
    """
    Protocol that is responsible for conversing with a POP server
    after a connection has been established.  Downloads messages (and
    deletes them by default), and passes the messages back up to the
    factory to process and turn into events.
    """

    allowInsecureLogin = True
    timeout = 15
    totalMessages = 0

    def serverGreeting(self, unused):
        log.debug('Server greeting received: Logging in...')

        login = self.login(self.factory.user, self.factory.passwd)
        login.addCallback(self._loggedIn)
        login.addErrback(self.factory.deferred.errback)

    def _loggedIn(self, unused):
        log.debug('Logged in')
        return self.retrieveAndParse()

    def retrieveAndParse(self):
        d = self.listSize()
        d.addCallback(self._gotMessageSizes)

        return d

    def _gotMessageSizes(self, sizes):
        self.totalMessages = len(sizes)
        log.info('Messages to retrieve: %d', self.totalMessages)

        self.sizes = sizes

        retreivers = []
        for i in range(len(sizes)):
            log.debug('Retrieving message #%d...', i)
            d = self.retrieve(i)
            d.addCallback(self._gotMessageLines)
            retreivers.append(d)

        deferreds = defer.DeferredList(retreivers) 
        deferreds.addCallback(self._delete)
        return deferreds.addCallback(self.scanComplete)

    def _gotMessageLines(self, messageLines):
        log.debug('Passing message up to factory')
        self.factory.handleMessage("\r\n".join(messageLines))

    def _delete(self, unused):
        deleters = []
        if not self.factory.nodelete:
            for index in range(len(self.sizes)):
                log.info('Deleting message  #%d...', index)
                d = self.delete(index)
                deleters.append(d)

        deferreds = defer.DeferredList(deleters)
        return deferreds

    def scanComplete(self, unused):
        log.debug("Scan complete")
        self.quit()
    
    
class POPFactory(protocol.ClientFactory):
    """
    Factory that stores the configuration the protocol uses to do
    its job.
    """
    protocol = POPProtocol

    def __init__(self, user, passwd, processor, nodelete):
        self.user = user
        self.passwd = passwd
        self.processor = processor
        self.deferred = defer.Deferred()
        self.nodelete = nodelete

    def handleMessage(self, messageData):
        self.processor.process(messageData)

    def clientConnectionFailed(self, unused, reason):
        self.deferred.errback(reason)


class MailCollectingTask(BaseTask):
    zope.interface.implements(IScheduledTask)

    STATE_COLLECTING = 'COLLECTING'

    def __init__(self, taskName, configId,
                 scheduleIntervalSeconds=60, taskConfig=None):
        BaseTask.__init__(self, taskName, configId,
                 scheduleIntervalSeconds, taskConfig)
        self.log = log

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self._preferences = taskConfig
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = self._daemon

        self.options = self._daemon.options

        # This will take a bit to catch up, but....
        self.interval = self.options.cycletime

        # Allow MailProcessor to work unmodified
        self.sendEvent = self._eventService.sendEvent

        self._daemon.changeUser()
        self.processor = POPProcessor(self,self.options.eventseverity)
        self._connection = None
        
    def doTask(self):
        d = defer.maybeDeferred(self.checkForMessages)
        return d

    def makeFactory(self):
        self.factory = POPFactory(self.options.popuser, self.options.poppass, 
            self.processor, self.options.nodelete)
        self.factory.deferred.addErrback(self.handleError)

    def checkForMessages(self):
        self.state = MailCollectingTask.STATE_COLLECTING

        self.makeFactory()
        if self.options.usessl:
            log.debug("Connecting to server %s:%s using SSL as %s",
                      self.options.pophost, self.options.popport, self.options.popuser)
            self._connection = reactor.connectSSL(self.options.pophost, self.options.popport,
                self.factory, ClientContextFactory())
        else:
            log.debug("Connecting to server %s:%s using plaintext as %s",
                      self.options.pophost, self.options.popport, self.options.popuser)
            self._connection = reactor.connectTCP(self.options.pophost, self.options.popport,
                self.factory)
        return defer.succeed("Connected to server %s:%s" % (
                             self.options.pophost, self.options.popport))

    def _finished(self, result=None):
        if self._connection:
            self._connection.disconnect()
        if self.factory:
            message = "Last retrieved %d messages" % self.factory.protocol.totalMessages
        else:
            message = "Completed"
        return defer.succeed(message)

    def handleError(self, err):
        if err.type == error.TimeoutError:
            message = "Timed out connecting to %s:%d" % (
                self.options.pophost, self.options.popport)

        elif err.type == error.ConnectionRefusedError:
            message = "Connection refused by %s:%d" % (
                self.options.pophost, self.options.popport)

        elif err.type == error.ConnectError:
            message = "Connection failed to %s:%d" % (
                self.options.pophost, self.options.popport)
        else:
            message = err.getErrorMessage()
            self.sendEvent(dict(
                device=socket.getfqdn(),
                component=COLLECTOR_NAME,
                severity=5,
                summary="Fatal error in %s" % COLLECTOR_NAME,
                message=message,
            ))
            
            self.state = TaskStates.STATE_IDLE

        log.error(message)
        return defer.succeed(message)

    def cleanup(self):
        self._finished()


if __name__=='__main__':
    myPreferences = MailPreferences()
    myTaskSplitter = NullTaskSplitter()
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
