##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import pkg_resources
from zenoss.protocols.eventlet.amqp import register_eventlet
from twisted.internet import reactor
from zope.component import adapter, getGlobalSiteManager
from Products.ZenEvents.zeneventd import ZenEventD
from Products.ZenEvents.daemonlifecycle import DaemonCreatedEvent, DaemonStartRunEvent
from Products.ZenEvents.daemonlifecycle import SigTermEvent, SigUsr1Event, BuildOptionsEvent
from Products.ZenCollector.utils.workers import ProcessWorkers, workersBuildOptions, exec_worker

@adapter(ZenEventD, SigTermEvent)
def onSigTerm(daemon, event):
    if daemon.options.daemon:
        daemon._workers.shutdown()

@adapter(ZenEventD, SigUsr1Event)
def onSigUsr1(daemon, event):
    if daemon.options.daemon:
        daemon._workers.sendSignal(event.signum)

@adapter(ZenEventD, BuildOptionsEvent)
def onBuildOptions(daemon, event):
    workersBuildOptions(daemon.parser, default=1)

@adapter(ZenEventD, DaemonCreatedEvent)
def onDaemonCreated(daemon, event):
    """
    Called at the end of zeneventd's constructor.
    """
    register_eventlet()
    if daemon.options.daemon or daemon.options.cycle:
        daemon._workers = ProcessWorkers(daemon.options.workers, exec_worker, "Event worker")

@adapter(ZenEventD, DaemonStartRunEvent)
def onDaemonStartRun(daemon, event):
    """
    Called when the daemon is ready to begin processing. This handler replaces the one
    defined in zeneventd.py, because onDaemonCreated (above) removes it
    """
    from .zeneventdWorkers import EventDEventletWorker
    # Free up unnecessary database resources in parent zeneventd process
    if daemon.options.daemon or daemon.options.cycle:
        daemon.closedb()
        daemon.closeAll()
        daemon._workers.startWorkers()
        reactor.run()
    else:
        worker = EventDEventletWorker()
        worker.run()
