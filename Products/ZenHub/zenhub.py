#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""zenhub daemon

Provide remote, authenticated, and possibly encrypted two-way
communications with the Model and Event databases.
"""
import Globals

if __name__ == "__main__":
    # Install the 'best' reactor available, BUT only if run as a script.
    from Products.ZenHub import installReactor
    installReactor()

from XmlRpcService import XmlRpcService

import collections
import heapq
import logging
from metrology import Metrology
from metrology.registry import registry
from metrology.instruments import Gauge
import time
import signal
import cPickle as pickle
import os
import subprocess
import itertools
from random import choice
from zope.component import getAdapters, subscribers

from twisted.cred import portal, checkers, credentials
from twisted.spread import pb, banana
banana.SIZE_LIMIT = 1024 * 1024 * 10

from twisted.internet import reactor, protocol, defer
from twisted.web import server, xmlrpc
from twisted.internet.error import ProcessExitedAlready
from twisted.internet.defer import inlineCallbacks, returnValue
from zope.event import notify
from zope.interface import implements
from zope.component import getUtility, getUtilitiesFor, adapts
from ZODB.POSException import POSKeyError

from Products.DataCollector.Plugins import loadPlugins
from Products.Five import zcml
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import zenPath, getExitMessage, unused, load_config, load_config_override, ipv6_available, atomicWrite, wait
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.MetricReporter import TwistedMetricReporter
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenEvents.ZenEventClasses import App_Start
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from Products.ZenRelations.PrimaryPathObjectManager import PrimaryPathObjectManager
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenHub.interfaces import IInvalidationProcessor, IServiceAddedEvent, IHubCreatedEvent, IHubWillBeCreatedEvent, IInvalidationOid, IHubConfProvider, IHubHeartBeatCheck
from Products.ZenHub.interfaces import IParserReadyForOptionsEvent, IInvalidationFilter
from Products.ZenHub.interfaces import FILTER_INCLUDE, FILTER_EXCLUDE
from Products.ZenHub.invalidations import INVALIDATIONS_PAUSED
from Products.ZenHub.WorkerSelection import WorkerSelector
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CRITICAL, SEVERITY_CLEAR
from Products.ZenUtils.metricwriter import MetricWriter, FilteredMetricWriter, AggregateMetricWriter
from Products.ZenUtils.metricwriter import ThresholdNotifier
from Products.ZenUtils.metricwriter import DerivativeTracker
from Products.ZenHub.metricpublisher.publisher import HttpPostPublisher, RedisListPublisher

from Products.ZenHub.PBDaemon import RemoteBadMonitor
pb.setUnjellyableForClass(RemoteBadMonitor, RemoteBadMonitor)

# Due to the manipulation of sys.path during the loading of plugins,
# we can get ObjectMap imported both as DataMaps.ObjectMap and the
# full-path from Products.  The following gets the class registered
# with the jelly serialization engine under both names:
#
#  1st: get Products.DataCollector.plugins.DataMaps.ObjectMap
from Products.DataCollector.plugins.DataMaps import ObjectMap
#  2nd: get DataMaps.ObjectMap
import sys
sys.path.insert(0, zenPath('Products', 'DataCollector', 'plugins'))
import DataMaps
unused(DataMaps, ObjectMap)

from Products.ZenHub import XML_RPC_PORT
from Products.ZenHub import PB_PORT
from Products.ZenHub import OPTION_STATE
from Products.ZenHub import CONNECT_TIMEOUT


from Products.ZenUtils.debugtools import ContinuousProfiler

HubWorklistItem = collections.namedtuple('HubWorklistItem', 'priority recvtime deferred servicename instance method args')
WorkerStats = collections.namedtuple('WorkerStats', 'status description lastupdate previdle')
LastCallReturnValue = collections.namedtuple('LastCallReturnValue', 'returnvalue')

try:
    NICE_PATH = subprocess.check_output('which nice', shell=True).strip()
except Exception:
    NICE_PATH = None

class AuthXmlRpcService(XmlRpcService):
    """Provide some level of authentication for XML/RPC calls"""

    def __init__(self, dmd, checker):
        XmlRpcService.__init__(self, dmd)
        self.checker = checker

    def doRender(self, unused, request):
        """
        Call the inherited render engine after authentication succeeds.
        See @L{XmlRpcService.XmlRpcService.Render}.
        """
        return XmlRpcService.render(self, request)

    def unauthorized(self, request):
        """
        Render an XMLRPC error indicating an authentication failure.
        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: None
        """
        self._cbRender(xmlrpc.Fault(self.FAILURE, "Unauthorized"), request)

    def render(self, request):
        """
        Unpack the authorization header and check the credentials.
        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: NOT_DONE_YET
        """
        auth = request.getHeader('authorization')
        if not auth:
            self.unauthorized(request)
        else:
            try:
                type, encoded = auth.split()
                if type not in ('Basic',):
                    self.unauthorized(request)
                else:
                    user, passwd = encoded.decode('base64').split(':')
                    c = credentials.UsernamePassword(user, passwd)
                    d = self.checker.requestAvatarId(c)
                    d.addCallback(self.doRender, request)
                    def error(unused, request):
                        self.unauthorized(request)
                    d.addErrback(error, request)
            except Exception:
                self.unauthorized(request)
        return server.NOT_DONE_YET


class HubAvitar(pb.Avatar):
    """
    Connect collectors to their configuration Services
    """

    def __init__(self, hub):
        self.hub = hub

    def perspective_ping(self):
        return 'pong'

    def perspective_getHubInstanceId(self):
        return os.environ.get('CONTROLPLANE_INSTANCE_ID', 'Unknown')

    def perspective_getService(self,
                               serviceName,
                               instance = None,
                               listener = None,
                               options = None):
        """
        Allow a collector to find a Hub service by name.  It also
        associates the service with a collector so that changes can be
        pushed back out to collectors.

        @type serviceName: string
        @param serviceName: a name, like 'EventService'
        @type instance: string
        @param instance: the collector's instance name, like 'localhost'
        @type listener: a remote reference to the collector
        @param listener: the callback interface to the collector
        @return a remote reference to a service
        """
        try:
            service = self.hub.getService(serviceName, instance)
        except RemoteBadMonitor:
            # This is a valid remote exception, so let it go through
            # to the collector daemon to handle
            raise
        except Exception:
            self.hub.log.exception("Failed to get service '%s'", serviceName)
            return None
        else:
            if service is not None and listener:
                service.addListener(listener, options)
            return service

    def perspective_reportingForWork(self, worker, pid=None):
        """
        Allow a worker register for work.

        @type worker: a pb.RemoteReference
        @param worker: a reference to zenhubworker
        @return None
        """
        worker.busy = False
        if pid is not None:
            worker.pid = pid
        self.hub.workers.append(worker)

        def removeWorker(worker):
            if worker in self.hub.workers:
                self.hub.workers.remove(worker)

        worker.notifyOnDisconnect(removeWorker)


class ServiceAddedEvent(object):
    implements(IServiceAddedEvent)

    def __init__(self, name, instance):
        self.name = name
        self.instance = instance


class HubWillBeCreatedEvent(object):
    implements(IHubWillBeCreatedEvent)

    def __init__(self, hub):
        self.hub = hub


class HubCreatedEvent(object):
    implements(IHubCreatedEvent)

    def __init__(self, hub):
        self.hub = hub


class ParserReadyForOptionsEvent(object):
    implements(IParserReadyForOptionsEvent)

    def __init__(self, parser):
        self.parser = parser


class HubRealm(object):
    """
    Following the Twisted authentication framework.
    See http://twistedmatrix.com/projects/core/documentation/howto/cred.html
    """
    implements(portal.IRealm)

    def __init__(self, hub):
        self.hubAvitar = HubAvitar(hub)

    def requestAvatar(self, collName, mind, *interfaces):
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        return pb.IPerspective, self.hubAvitar, lambda:None


class WorkerInterceptor(pb.Referenceable):
    """Redirect service requests to one of the worker processes. Note
    that everything else (like change notifications) go through
    locally hosted services."""

    callTime = 0.

    def __init__(self, zenhub, service):
        self.zenhub = zenhub
        self.service = service
        self._serviceCalls = Metrology.meter("zenhub.serviceCalls")
        self.log = logging.getLogger('zen.zenhub.WorkerInterceptor')
        self._admTimer = Metrology.timer('zenhub.applyDataMap')


    def remoteMessageReceived(self, broker, message, args, kw):
        """Intercept requests and send them down to workers"""
        self._serviceCalls.mark()
        svc = str(self.service.__class__).rpartition('.')[0]
        instance = self.service.instance
        args = broker.unserialize(args)
        kw = broker.unserialize(kw)
        # hide the types in the args: subverting the jelly protection mechanism,
        # but the types just passed through and the worker may not have loaded
        # the required service before we try passing types for that service
        # PB has a 640k limit, not bytes but len of sequences. When args are
        # pickled the resulting string may be larger than 640k, split into
        # 100k chunks
        pickledArgs = pickle.dumps( (args, kw), pickle.HIGHEST_PROTOCOL )
        chunkedArgs=[]
        chunkSize = 102400
        while pickledArgs:
            chunk = pickledArgs[:chunkSize]
            chunkedArgs.append(chunk)
            pickledArgs = pickledArgs[chunkSize:]

        start = time.time()
        def recordTime(result):
            #get in milliseconds
            duration = int((time.time() - start) * 1000)
            self._admTimer.update(duration)
            return result

        deferred = self.zenhub.deferToWorker(svc, instance, message, chunkedArgs)

        if message == 'applyDataMaps':
            deferred.addCallback(recordTime)

        return broker.serialize(deferred, self.perspective)

    def __getattr__(self, attr):
        """Implement the HubService interface by forwarding to the local service"""
        return getattr(self.service, attr)


class _ZenHubWorklist(object):

    def __init__(self):
        self.eventworklist = []
        self.otherworklist = []
        self.applyworklist = []

        #priority lists for eventual task selection. All queues are appended in case
        #any of them are empty.
        self.eventPriorityList = [self.eventworklist, self.otherworklist, self.applyworklist]
        self.otherPriorityList = [self.otherworklist, self.applyworklist, self.eventworklist]
        self.applyPriorityList = [self.applyworklist, self.eventworklist, self.otherworklist]
        self.dispatch = {
            'sendEvents': self.eventworklist,
            'sendEvent': self.eventworklist,
            'applyDataMaps': self.applyworklist
        }

    def __getitem__(self, item):
        return self.dispatch.get(item, self.otherworklist)

    def __len__(self):
        return len(self.eventworklist) + len(self.otherworklist) + len(self.applyworklist)

    def pop(self, allowADM=True):
        """
        Select a single task to be distributed to a worker. We prioritize tasks as follows:
            sendEvents > configuration service calls > applyDataMaps
        To prevent starving any queue in an event storm, we randomize the task selection,
        preferring tasks according to the above priority.

        allowADM controls whether we should allow popping jobs from the applyDataMaps list,
        this should be False while models are changing (like during a zenpack install/upgrade/removal)
        """
        # the priority lists have eventworklist, otherworklist, and applyworklist
        # when we don't want to allow ApplyDataMaps, we should exclude the possibility of popping from applyworklist
        eventchain = filter(None, self.eventPriorityList if allowADM else [self.eventworklist, self.otherworklist])
        otherchain = filter(None, self.otherPriorityList if allowADM else [self.otherworklist, self.eventworklist])
        applychain = filter(None, self.applyPriorityList if allowADM else [self.eventworklist, self.otherworklist])

        # choose a job to pop based on weighted random
        choice_list = [eventchain]*4 + [otherchain]*2 + [applychain]
        chosen_list = choice(choice_list)
        if len(chosen_list) > 0:
            item = heapq.heappop(chosen_list[0])
            return item
        else:
            return None

    def push(self, job):
        heapq.heappush(self[job.method], job)
    append = push

def publisher(username, password, url):
    return HttpPostPublisher( username, password, url)

def redisPublisher():
    return RedisListPublisher()

def metricWriter():
    metric_writer = MetricWriter(redisPublisher())
    if os.environ.get( "CONTROLPLANE", "0") == "1":
        internal_url = os.environ.get( "CONTROLPLANE_CONSUMER_URL", None)
        internal_username = os.environ.get( "CONTROLPLANE_CONSUMER_USERNAME", "")
        internal_password = os.environ.get( "CONTROLPLANE_CONSUMER_PASSWORD", "")

        if internal_url:
            internal_publisher = publisher( internal_username, internal_password, internal_url)
            internal_metric_filter = lambda metric, value, timestamp, tags:\
                tags and tags.get("internal", False)
            internal_metric_writer = FilteredMetricWriter(internal_publisher, internal_metric_filter)
            return AggregateMetricWriter( [metric_writer, internal_metric_writer])

    return metric_writer


class ZenHub(ZCmdBase):
    """
    Listen for changes to objects in the Zeo database and update the
    collectors' configuration.

    The remote collectors connect the ZenHub and request configuration
    information and stay connected.  When changes are detected in the
    Zeo database, configuration updates are sent out to collectors
    asynchronously.  In this way, changes made in the web GUI can
    affect collection immediately, instead of waiting for a
    configuration cycle.

    Each collector uses a different, pluggable service within ZenHub
    to translate objects into configuration and data.  ZenPacks can
    add services for their collectors.  Collectors communicate using
    Twisted's Perspective Broker, which provides authenticated,
    asynchronous, bidirectional method invocation.

    ZenHub also provides an XmlRPC interface to some common services
    to support collectors written in other languages.

    ZenHub does very little work in its own process, but instead dispatches
    the work to a pool of zenhubworkers, running zenhubworker.py. zenhub
    manages these workers with 3 data structures:
    - workers - a list of remote PB instances
    - worker_processes - a set of WorkerRunningProtocol instances
    - workerprocessmap - a dict mapping pid to process instance created
        by reactor.spawnprocess
    Callbacks and handlers that detect worker shutdown update these
    structures automatically. ONLY ONE HANDLER must take care of restarting
    new workers, to avoid accidentally spawning too many workers. This
    handler also verifies that zenhub is not in the process of shutting
    down, so that callbacks triggered during daemon shutdown don't keep
    starting new workers.

    TODO: document invalidation workers
    """

    totalTime = 0.
    totalEvents = 0
    totalCallTime = 0.
    name = 'zenhub'

    def __init__(self):
        """
        Hook ourselves up to the Zeo database and wait for collectors
        to connect.
        """
        # list of remote worker references
        self.workers = []
        self.workTracker = {}
        # zenhub execution stats: [count, idle_total, running_total, last_called_time]
        self.executionTimer = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
        self.workList = _ZenHubWorklist()
        # set of worker processes
        self.worker_processes=set()
        # map of worker pids -> worker processes
        self.workerprocessmap = {}
        self.shutdown = False
        self.counters = collections.Counter()
        self._invalidations_paused = False

        wl = self.workList
        metricNames = {x[0] for x in registry}
        class EventWorkList(Gauge):
            @property
            def value(self):
                return len(wl.eventworklist)
        if 'zenhub.eventWorkList' not in metricNames:
            Metrology.gauge('zenhub.eventWorkList', EventWorkList())

        class ADMWorkList(Gauge):
            @property
            def value(self):
                return len(wl.applyworklist)
        if 'zenhub.admWorkList' not in metricNames:
            Metrology.gauge('zenhub.admWorkList', ADMWorkList())

        class OtherWorkList(Gauge):
            @property
            def value(self):
                return len(wl.otherworklist)
        if 'zenhub.otherWorkList' not in metricNames:
            Metrology.gauge('zenhub.otherWorkList', OtherWorkList())

        class WorkListTotal(Gauge):
            @property
            def value(self):
                return len(wl)
        if 'zenhub.workList' not in metricNames:
            Metrology.gauge('zenhub.workList', WorkListTotal())

        ZCmdBase.__init__(self)
        import Products.ZenHub
        load_config("hub.zcml", Products.ZenHub)
        notify(HubWillBeCreatedEvent(self))

        if self.options.profiling:
            self.profiler = ContinuousProfiler('zenhub', log=self.log)
            self.profiler.start()

        #Worker selection handler
        self.workerselector = WorkerSelector(self.options)
        self.workList.log = self.log

        # make sure we don't reserve more than n-1 workers for events
        maxReservedEventsWorkers = 0
        if self.options.workers:
            maxReservedEventsWorkers = self.options.workers - 1
        if self.options.workersReservedForEvents > maxReservedEventsWorkers:
            self.options.workersReservedForEvents = maxReservedEventsWorkers
            self.log.info("reduced number of workers reserved for sending events to %d",
                          self.options.workersReservedForEvents)

        self.zem = self.dmd.ZenEventManager
        loadPlugins(self.dmd)
        self.services = {}

        er = HubRealm(self)
        checker = self.loadChecker()
        pt = portal.Portal(er, [checker])
        interface = '::' if ipv6_available() else ''
        pbport = reactor.listenTCP(self.options.pbport, pb.PBServerFactory(pt), interface=interface)
        self.setKeepAlive(pbport.socket)

        xmlsvc = AuthXmlRpcService(self.dmd, checker)
        reactor.listenTCP(self.options.xmlrpcport, server.Site(xmlsvc), interface=interface)

        # responsible for sending messages to the queues
        import Products.ZenMessaging.queuemessaging
        load_config_override('twistedpublisher.zcml', Products.ZenMessaging.queuemessaging)
        notify(HubCreatedEvent(self))
        self.sendEvent(eventClass=App_Start,
                       summary="%s started" % self.name,
                       severity=0)

        self._initialize_invalidation_filters()
        reactor.callLater(self.options.invalidation_poll_interval, self.processQueue)

        self._metric_writer = metricWriter()
        self.rrdStats = self.getRRDStats()

        if self.options.workers:
            self.workerconfig = zenPath('var', 'zenhub', '%s_worker.conf' % self._getConf().id)
            self._createWorkerConf()
            for i in range(self.options.workers):
                self.createWorker(i)

            # start cyclic call to giveWorkToWorkers
            reactor.callLater(2, self.giveWorkToWorkers, True)

        # set up SIGUSR2 handling
        try:
            signal.signal(signal.SIGUSR2, self.sighandler_USR2)
        except ValueError:
            # If we get called multiple times, this will generate an exception:
            # ValueError: signal only works in main thread
            # Ignore it as we've already set up the signal handler.
            pass
        # ZEN-26671 Wait at least this duration in secs before signaling a worker process
        self.SIGUSR_TIMEOUT = 5

    def setKeepAlive(self, sock):
        import socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT)
        interval = max(CONNECT_TIMEOUT / 4, 10)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)
        self.log.debug("set socket%s  CONNECT_TIMEOUT:%d  TCP_KEEPINTVL:%d", sock.getsockname(), CONNECT_TIMEOUT, interval)

    def sighandler_USR2(self, signum, frame):
        #log zenhub's worker stats
        self._workerStats()

        # send SIGUSR2 signal to all workers
        now = time.time()
        for worker in self.workerprocessmap.values():
            try:
                elapsed_since_spawn = now - worker.spawn_time
                self.log.debug('{} secs elapsed since this worker proc was spawned'.format(elapsed_since_spawn))
                if elapsed_since_spawn >= self.SIGUSR_TIMEOUT:
                    worker.signalProcess(signal.SIGUSR2)
                time.sleep(0.5)
            except Exception:
                pass

    def sighandler_USR1(self, signum, frame):
        #handle it ourselves
        if self.options.profiling:
            self.profiler.dump_stats()

        super(ZenHub, self).sighandler_USR1(signum, frame)

        # send SIGUSR1 signal to all workers
        for worker in self.workerprocessmap.values():
            try:
                worker.signalProcess(signal.SIGUSR1)
                time.sleep(0.5)
            except Exception:
                pass

    def stop(self):
        self.shutdown = True

    def _getConf(self):
        confProvider = IHubConfProvider(self)
        return confProvider.getHubConf()

    def getRRDStats(self):
        """
        Return the most recent RRD statistic information.
        """
        rrdStats = DaemonStats()
        perfConf = self._getConf()

        from Products.ZenModel.BuiltInDS import BuiltInDS
        threshs = perfConf.getThresholdInstances(BuiltInDS.sourcetype)
        threshold_notifier = ThresholdNotifier(self.zem.sendEvent, threshs)

        derivative_tracker = DerivativeTracker()

        rrdStats.config('zenhub', perfConf.id, self._metric_writer,
                        threshold_notifier, derivative_tracker)

        return rrdStats

    @defer.inlineCallbacks
    def processQueue(self):
        """
        Periodically process database changes

        @return: None
        """
        now = time.time()
        try:
            self.log.debug("[processQueue] syncing....")
            yield self.async_syncdb()  # reads the object invalidations
            self.log.debug("[processQueue] synced")
        except Exception:
            self.log.warn("Unable to poll invalidations, will try again.")
        else:
            try:
                self.doProcessQueue()
            except Exception, ex:
                self.log.exception("Unable to poll invalidations.")
        reactor.callLater(self.options.invalidation_poll_interval, self.processQueue)
        self.totalEvents += 1
        self.totalTime += time.time() - now

    def _initialize_invalidation_filters(self):
        filters = (f for n, f in getUtilitiesFor(IInvalidationFilter))
        self._invalidation_filters = []
        for fltr in sorted(filters, key=lambda f:getattr(f, 'weight', 100)):
            fltr.initialize(self.dmd)
            self._invalidation_filters.append(fltr)
        self.log.debug('Registered %s invalidation filters.' %
                       len(self._invalidation_filters))

    def _filter_oids(self, oids):
        app = self.dmd.getPhysicalRoot()
        i = 0
        for oid in oids:
            i += 1
            try:
                obj = app._p_jar[oid]
            except POSKeyError:
                # State is gone from the database. Send it along.
                yield oid
            else:
                if isinstance(obj, (PrimaryPathObjectManager, DeviceComponent)):
                    try:
                        obj = obj.__of__(self.dmd).primaryAq()
                    except (AttributeError, KeyError):
                        # It's a delete. This should go through.
                        yield oid
                    else:
                        included = True
                        for fltr in self._invalidation_filters:
                            result = fltr.include(obj)
                            if result in (FILTER_INCLUDE, FILTER_EXCLUDE):
                                included = (result == FILTER_INCLUDE)
                                break
                        if included:
                            oids = self._transformOid(oid, obj)
                            if oids:
                                for oid in oids:
                                    yield oid

    def _transformOid(self, oid, obj):
        # First, get any subscription adapters registered as transforms
        adapters = subscribers((obj,), IInvalidationOid)
        # Next check for an old-style (regular adapter) transform
        try:
            adapters = itertools.chain(adapters, (IInvalidationOid(obj),))
        except TypeError:
            # No old-style adapter is registered
            pass
        transformed = set()
        for adapter in adapters:
            o = adapter.transformOid(oid)
            if isinstance(o, basestring):
                transformed.add(o)
            elif hasattr(o, '__iter__'):
                # If the transform didn't give back a string, it should have
                # given back an iterable
                transformed.update(o)
        # Get rid of any useless Nones
        transformed.discard(None)
        # Get rid of the original oid, if returned. We don't want to use it IF
        # any transformed oid came back.
        transformed.discard(oid)
        return transformed or (oid,)

    def doProcessQueue(self):
        """
        Perform one cycle of update notifications.

        @return: None
        """
        changes_dict = self.storage.poll_invalidations()
        if changes_dict is not None:
            processor = getUtility(IInvalidationProcessor)
            d = processor.processQueue(tuple(set(self._filter_oids(changes_dict))))

            def done(n):
                if n == INVALIDATIONS_PAUSED:
                    self.sendEvent({'summary': "Invalidation processing is "
                                               "currently paused. To resume, set "
                                               "'dmd.pauseHubNotifications = False'",
                                    'severity': SEVERITY_CRITICAL,
                                    'eventkey': INVALIDATIONS_PAUSED})
                    self._invalidations_paused = True
                else:
                    msg = 'Processed %s oids' % n
                    self.log.debug(msg)
                    if self._invalidations_paused:
                        self.sendEvent({'summary': msg,
                                        'severity': SEVERITY_CLEAR,
                                        'eventkey': INVALIDATIONS_PAUSED})
                        self._invalidations_paused = False
            d.addCallback(done)

    def sendEvent(self, **kw):
        """
        Useful method for posting events to the EventManager.

        @type kw: keywords (dict)
        @param kw: the values for an event: device, summary, etc.
        @return: None
        """
        if not 'device' in kw:
            kw['device'] = self.options.monitor
        if not 'component' in kw:
            kw['component'] = self.name
        try:
            self.zem.sendEvent(Event(**kw))
        except Exception:
            self.log.exception("Unable to send an event")

    def loadChecker(self):
        """
        Load the password file

        @return: an object satisfying the ICredentialsChecker
        interface using a password file or an empty list if the file
        is not available.  Uses the file specified in the --passwd
        command line option.
        """
        try:
            checker = checkers.FilePasswordDB(self.options.passwordfile)
            # grab credentials for the workers to login
            u, p = checker._loadCredentials().next()
            self.workerUsername, self.workerPassword = u, p
            return checker
        except Exception, ex:
            self.log.exception("Unable to load %s", self.options.passwordfile)
        return []

    def getService(self, name, instance):
        """
        Helper method to load services dynamically for a collector.
        Returned instances are cached: reconnecting collectors will
        get the same service object.

        @type name: string
        @param name: the dotted-name of the module to load
        (uses @L{Products.ZenUtils.Utils.importClass})
        @param instance: string
        @param instance: each service serves only one specific collector
        instances (like 'localhost').  instance defines the collector's
        instance name.
        @return: a service loaded from ZenHub/services or one of the zenpacks.
        """
        # Sanity check the names given to us
        if not self.dmd.Monitors.Performance._getOb(instance, False):
            raise RemoteBadMonitor("The provided performance monitor '%s'" %
                                   instance +
                                   " is not in the current list", None)

        try:
            return self.services[name, instance]

        except KeyError:
            from Products.ZenUtils.Utils import importClass
            try:
                ctor = importClass(name)
            except ImportError:
                ctor = importClass('Products.ZenHub.services.%s' % name, name)
            try:
                svc = ctor(self.dmd, instance)
            except Exception:
                self.log.exception("Failed to initialize %s", ctor)
                # Module can't be used, so unload it.
                if ctor.__module__ in sys.modules:
                    del sys.modules[ctor.__module__]
                return None
            else:
                if self.options.workers:
                    svc = WorkerInterceptor(self, svc)
                self.services[name, instance] = svc
                notify(ServiceAddedEvent(name, instance))
                return svc

    def deferToWorker(self, svcName, instance, method, args):
        """Take a remote request and queue it for worker processes.

        @type svcName: string
        @param svcName: the name of the hub service to call
        @type instance: string
        @param instance: the name of the hub service instance to call
        @type method: string
        @param method: the name of the method on the hub service to call
        @type args: tuple
        @param args: the remaining arguments to the remote_execute() method in the worker
        @return: a Deferred for the eventual results of the method call
        """
        d = defer.Deferred()
        service = self.getService(svcName, instance).service
        priority = service.getMethodPriority(method)

        self.workList.append(
            HubWorklistItem(priority, time.time(), d, svcName, instance, method,
                            (svcName, instance, method, args)))

        reactor.callLater(0, self.giveWorkToWorkers)
        return d

    def updateStatusAtStart(self, wId, job):
        now = time.time()
        jobDesc = "%s:%s.%s" % (job.instance, job.servicename, job.method)
        stats = self.workTracker.pop(wId, None)
        idletime = now - stats.lastupdate if stats else 0
        self.executionTimer[job.method][0] += 1
        self.executionTimer[job.method][1] += idletime
        self.executionTimer[job.method][3] = now
        self.log.debug("Giving %s to worker %d, (%s)", job.method, wId, jobDesc)
        self.workTracker[wId] = WorkerStats('Busy', jobDesc, now, idletime)

    def updateStatusAtFinish(self, wId, job, error=None):
        now = time.time()
        self.executionTimer[job.method][3] = now
        stats = self.workTracker.pop(wId, None)
        if stats:
            elapsed = now - stats.lastupdate
            self.executionTimer[job.method][2] += elapsed
            self.log.debug("worker %s, work %s finished in %s" % (wId, stats.description, elapsed))
        self.workTracker[wId] = WorkerStats('Error: %s' % error if error else 'Idle',
                                            stats.description, now, 0)

    @inlineCallbacks
    def finished(self, job, result, finishedWorker, wId):
        finishedWorker.busy = False
        error = None
        if isinstance(result, Exception):
            job.deferred.errback(result)
        else:
            try:
                self.log.debug("worker %s result -> %s", wId, result)
                result = pickle.loads(''.join(result))
            except Exception as e:
                error = e
                self.log.exception("Error un-pickling result from worker")

            # if zenhubworker is about to shutdown, it will wrap the actual result
            # in a LastCallReturnValue tuple - remove worker from worker list to
            # keep from accidentally sending it any more work while it shuts down
            if isinstance(result, LastCallReturnValue):
                self.log.debug("worker %s is shutting down" % wId)
                result = result.returnvalue
                if finishedWorker in self.workers:
                    self.workers.remove(finishedWorker)

            #the job contains a deferred to be used to return the actual value
            job.deferred.callback(result)

        self.updateStatusAtFinish(wId, job, error)
        reactor.callLater(0.1, self.giveWorkToWorkers)
        yield returnValue(result)

    @inlineCallbacks
    def giveWorkToWorkers(self, requeue=False):
        """Parcel out a method invocation to an available worker process
        """
        if self.workList:
            self.log.debug("worklist has %d items", len(self.workList))
        incompleteJobs = []
        while self.workList:
            if all(w.busy for w in self.workers):
                self.log.debug("all workers are busy")
                yield wait(0.1)
                break

            allowADM = self.dmd.getPauseADMLife() > self.options.modeling_pause_timeout
            job = self.workList.pop(allowADM)
            if job is None:
                self.log.info("Got None from the job worklist.  ApplyDataMaps may be paused for zenpack install/upgrade/removal.")
                yield wait(0.1)
                break

            candidateWorkers = list(self.workerselector.getCandidateWorkerIds(job.method, self.workers))
            for i in candidateWorkers:
                worker = self.workers[i]
                worker.busy = True
                self.counters['workerItems'] += 1
                self.updateStatusAtStart(i, job)
                try:
                    result = yield worker.callRemote('execute', *job.args)
                except Exception as ex:
                    self.log.warning("Failed to execute job on zenhub worker")
                    result = ex
                finally:
                    yield self.finished(job, result, worker, i)
                break
            else:
                #could not complete this job, put it back in the queue once
                #we're finished saturating the workers
                incompleteJobs.append(job)

        for job in reversed(incompleteJobs):
            #could not complete this job, put it back in the queue
            self.workList.push(job)

        if incompleteJobs:
            self.log.debug("No workers available for %d jobs." % len(incompleteJobs))
            reactor.callLater(0.1, self.giveWorkToWorkers)

        if requeue and not self.shutdown:
            reactor.callLater(5, self.giveWorkToWorkers, True)

    def _workerStats(self):
        now = time.time()
        lines = ['Worklist Stats:',
                 '\tEvents:\t%s' % len(self.workList.eventworklist),
                 '\tOther:\t%s' % len(self.workList.otherworklist),
                 '\tApplyDataMaps:\t%s' % len(self.workList.applyworklist),
                 '\tTotal:\t%s' % len(self.workList),
                 '\nHub Execution Timings: [method, count, idle_total, running_total, last_called_time]'
                 ]

        statline = " - %-32s %8d %12.2f %8.2f  %s"
        for method, stats in sorted(self.executionTimer.iteritems(), key=lambda v: -v[1][2]):
            lines.append(statline %
                         (method, stats[0], stats[1], stats[2],
                          time.strftime("%Y-%d-%m %H:%M:%S", time.localtime(stats[3]))))

        lines.append('\nWorker Stats:')
        for wId, worker in enumerate(self.workers):
            stat = self.workTracker.get(wId, None)
            linePattern = '\t%d(pid=%s):%s\t[%s%s]\t%.3fs'
            lines.append(linePattern % (
                wId,
                '{}'.format(worker.pid),
                'Busy' if worker.busy else 'Idle',
                '%s %s' % (stat.status, stat.description) if stat else 'No Stats',
                ' Idle:%.3fs' % stat.previdle if stat and stat.previdle else '',
                now - stat.lastupdate if stat else 0
            ))
            if stat:
                if (worker.busy and stat.status is 'Idle') or (not worker.busy and stat.status is 'Busy'):
                    self.log.warn('worker.busy: {} and stat.status: {} do not match!'.format(worker.busy, stat.status))
        self.log.info('\n'.join(lines))

    def _createWorkerConf(self):
        workerconfigdir = os.path.dirname(self.workerconfig)
        if not os.path.exists(workerconfigdir):
            os.makedirs(workerconfigdir)
        with open(self.workerconfig, 'w') as workerfd:
            workerfd.write("hubport %s\n" % self.options.pbport)
            workerfd.write("username %s\n" % self.workerUsername)
            workerfd.write("password %s\n" % self.workerPassword)
            workerfd.write("logseverity %s\n" % self.options.logseverity)
            workerfd.write("zodb-cachesize %s\n" % self.options.zodb_cachesize)
            workerfd.write("calllimit %s\n" % self.options.worker_call_limit)
            workerfd.write("profiling %s\n" % self.options.profiling)
            workerfd.write("monitor %s\n" % self.options.monitor)

    def createWorker(self, workerNum):
        """Start a worker subprocess

        @return: None
        """
        # this probably can't happen, but let's make sure
        if len(self.worker_processes) >= self.options.workers:
            self.log.info("already at maximum number of worker processes, no worker will be created")
            return

        # watch for output, and generally just take notice
        class WorkerRunningProtocol(protocol.ProcessProtocol):

            def __init__(self, parent, workerNum):
                self._pid = 0
                self.parent = parent
                self.log = parent.log
                self.workerNum = workerNum

            @property
            def pid(self):
                return self._pid

            def connectionMade(self):
                self._pid = self.transport.pid
                reactor.callLater(1, self.parent.giveWorkToWorkers)

            def outReceived(self, data):
                self.log.debug("Worker %d (%d) reports %s" % (self.workerNum, self.pid, data.rstrip(),))

            def errReceived(self, data):
                self.log.info("Worker %d (%d) reports %s" % (self. workerNum, self.pid, data.rstrip(),))

            def processEnded(self, reason):
                self.parent.worker_processes.discard(self)
                ended_proc = self.parent.workerprocessmap.pop(self.pid, None)
                ended_proc_age = time.time() - ended_proc.spawn_time
                self.log.warning("Worker %d (%d), age %f secs, exited with status: %d (%s)",
                                 self.workerNum,
                                 self.pid,
                                 ended_proc_age,
                                  reason.value.exitCode or -1,
                                  getExitMessage(reason.value.exitCode))
                # if not shutting down, restart a new worker
                if not self.parent.shutdown:
                    self.log.info("Starting new zenhubworker")
                    self.parent.createWorker(self.workerNum)

        if NICE_PATH:
            exe = NICE_PATH
            args = (NICE_PATH, "-n", "%+d" % self.options.hubworker_priority,
                    zenPath('bin', 'zenhubworker'), 'run', '--workernum', '%s' % workerNum, '-C', self.workerconfig)
        else:
            exe = zenPath('bin', 'zenhubworker')
            args = (exe, 'run', '-C', self.workerconfig)
        self.log.debug("Starting %s", ' '.join(args))
        prot = WorkerRunningProtocol(self, workerNum)
        proc = reactor.spawnProcess(prot, exe, args, os.environ)
        proc.spawn_time = time.time()
        self.workerprocessmap[proc.pid] = proc
        self.worker_processes.add(prot)

    def heartbeat(self):
        """
        Since we don't do anything on a regular basis, just
        push heartbeats regularly.

        @return: None
        """
        seconds = 30
        evt = EventHeartbeat(self.options.monitor, self.name, self.options.heartbeatTimeout)
        self.zem.sendEvent(evt)
        self.niceDoggie(seconds)
        reactor.callLater(seconds, self.heartbeat)
        r = self.rrdStats
        totalTime = sum(s.callTime for s in self.services.values())
        r.counter('totalTime', int(self.totalTime * 1000))
        r.counter('totalEvents', self.totalEvents)
        r.gauge('services', len(self.services))
        r.counter('totalCallTime', totalTime)
        r.gauge('workListLength', len(self.workList))

        for name, value in self.counters.items():
            r.counter(name, value)

        # persist counters values
        self.saveCounters()
        try:
            hbcheck = IHubHeartBeatCheck(self)
            hbcheck.check()
        except:
            self.log.exception("Error processing heartbeat hook")

    def saveCounters(self):
        atomicWrite(
            zenPath('var/zenhub_counters.pickle'),
            pickle.dumps(self.counters),
            raiseException=False,
        )

    def loadCounters(self):
        try:
            self.counters = pickle.load(open(zenPath('var/zenhub_counters.pickle')))
        except Exception:
            pass

    def main(self):
        """
        Start the main event loop.
        """
        if self.options.cycle:
            reactor.callLater(0, self.heartbeat)
            self.log.debug("Creating async MetricReporter")
            daemonTags = {
                'zenoss_daemon': 'zenhub',
                'zenoss_monitor': self.options.monitor,
                'internal': True
            }
            self.metricreporter = TwistedMetricReporter(metricWriter=self._metric_writer, tags=daemonTags)
            self.metricreporter.start()
            reactor.addSystemEventTrigger('before', 'shutdown', self.metricreporter.stop)

        reactor.run()
        self.shutdown = True
        self.log.debug("Killing workers")
        for proc in self.workerprocessmap.itervalues():
            try:
                proc.signalProcess('KILL')
                self.log.debug("Killed worker %s", proc)
            except ProcessExitedAlready:
                pass
            except Exception:
                pass
        workerconfig = getattr(self,'workerconfig', None)
        if workerconfig and os.path.exists(workerconfig):
            os.unlink(self.workerconfig)
        getUtility(IEventPublisher).close()
        if self.options.profiling:
            self.profiler.stop()

    def buildOptions(self):
        """
        Adds our command line options to ZCmdBase command line options.
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--xmlrpcport', '-x', dest='xmlrpcport',
            type='int', default=XML_RPC_PORT,
            help='Port to use for XML-based Remote Procedure Calls (RPC)')
        self.parser.add_option('--pbport', dest='pbport',
            type='int', default=PB_PORT,
            help="Port to use for Twisted's pb service")
        self.parser.add_option('--passwd', dest='passwordfile',
            type='string', default=zenPath('etc','hubpasswd'),
            help='File where passwords are stored')
        self.parser.add_option('--monitor', dest='monitor',
            default='localhost',
            help='Name of the distributed monitor this hub runs on')
        self.parser.add_option('--workers', dest='workers',
            type='int', default=2,
            help="Number of worker instances to handle requests")
        self.parser.add_option('--hubworker-priority', type='int', default=5,
            help="Relative process priority for hub workers (%default)")
        self.parser.add_option('--prioritize', dest='prioritize',
            action='store_true', default=False,
            help="Run higher priority jobs before lower priority ones")
        self.parser.add_option('--anyworker', dest='anyworker',
            action='store_true', default=False,
            help='Allow any priority job to run on any worker')
        self.parser.add_option('--workers-reserved-for-events', dest='workersReservedForEvents',
            type='int', default=1,
            help="Number of worker instances to reserve for handling events")
        self.parser.add_option('--worker-call-limit', dest='worker_call_limit',
            type='int', default=200,
            help="Maximum number of remote calls a worker can run before restarting")
        self.parser.add_option('--invalidation-poll-interval',
            type='int', default=30,
            help="Interval at which to poll invalidations (default: %default)")
        self.parser.add_option('--profiling', dest='profiling',
            action='store_true', default=False,
            help="Run with profiling on")
        self.parser.add_option('--modeling-pause-timeout',
            type='int', default=3600,
            help="Maximum number of seconds to pause modeling during ZenPack install/upgrade/removal (default: %default)")

        notify(ParserReadyForOptionsEvent(self.parser))

class DefaultConfProvider(object):
    implements(IHubConfProvider)
    adapts(ZenHub)

    def __init__(self, zenhub):
        self._zenhub = zenhub

    def getHubConf(self):
        zenhub = self._zenhub
        return zenhub.dmd.Monitors.Performance._getOb(zenhub.options.monitor, None)

class DefaultHubHeartBeatCheck(object):
    implements(IHubHeartBeatCheck)
    adapts(ZenHub)

    def __init__(self, zenhub):
        self._zenhub = zenhub

    def check(self):
        pass


if __name__ == '__main__':
    from Products.ZenHub.zenhub import ZenHub
    z = ZenHub()

    # during startup, restore performance counters
    z.loadCounters()

    z.main()

    # during shutdown, attempt to save our performance counters
    z.saveCounters()
