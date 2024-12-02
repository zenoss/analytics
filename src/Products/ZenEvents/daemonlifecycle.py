##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.component.interfaces import ObjectEvent

class DaemonLifecycleEvent(ObjectEvent):
    """
    Base class for zeneventd lifecycle events.
    """

class DaemonCreatedEvent(DaemonLifecycleEvent):
    """
    Fired at the end of zeneventd's constructor.
    """

class DaemonStartRunEvent(DaemonLifecycleEvent):
    """
    Fired when zeneventd is started and ready to listen.
    """

class SigTermEvent(DaemonLifecycleEvent):
    """
    Called when zeneventd receives a SIGTERM.
    """

class SigUsr1Event(DaemonLifecycleEvent):
    """
    Called when zeneventd receives a SIGUSR1 event -- that is,
    when "zeneventd debug" is run.
    """
    def __init__(self, daemon, signum):
        super(SigUsr1Event, self).__init__(daemon)
        self.signum = signum

class BuildOptionsEvent(DaemonLifecycleEvent):
    """
    Called when zeneventd is building its option parser.
    """
