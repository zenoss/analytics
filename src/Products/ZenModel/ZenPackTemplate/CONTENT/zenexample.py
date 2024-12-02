# This is an example of a custom collector daemon.

import logging
log = logging.getLogger('zen.Example')

import Globals
import zope.component
import zope.interface

from twisted.internet import defer

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces \
    import ICollectorPreferences, IScheduledTask, IEventService, IDataService

from Products.ZenCollector.tasks \
    import SimpleTaskFactory, SimpleTaskSplitter, TaskStates

from Products.ZenUtils.observable import ObservableMixin

# unused is way to keep Python linters from complaining about imports that we
# don't explicitely use. Occasionally there is a valid reason to do this.
from Products.ZenUtils.Utils import unused

# We must import our ConfigService here so zenhub will allow it to be
# serialized and deserialized. We'll declare it unused to satisfy linters.
from ZenPacks.NAMESPACE.PACKNAME.services.ExampleConfigService \
    import ExampleConfigService

unused(Globals)
unused(ExampleConfigService)


# Your implementation of ICollectorPreferences is where you can handle custom
# command line (or config file) options and do global configuration of the
# daemon.
class ZenExamplePreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        self.collectorName = 'zenexample'
        self.configurationService = \
            "ZenPacks.NAMESPACE.PACKNAME.services.ExampleConfigService"

        # How often the daemon will collect each device. Specified in seconds.
        self.cycleInterval = 5 * 60

        # How often the daemon will reload configuration. In seconds.
        self.configCycleInterval = 5 * 60

        self.options = None

    def buildOptions(self, parser):
        """
        Required to implement the ICollectorPreferences interface.
        """
        pass

    def postStartup(self):
        """
        Required to implement the ICollectorPreferences interface.
        """
        pass


# The implementation of IScheduledTask for your daemon is usually where most
# of the work is done. This is where you implement the specific logic required
# to collect data.
class ZenExampleTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)

    def __init__(self, taskName, deviceId, interval, taskConfig):
        super(ZenExampleTask, self).__init__()
        self._taskConfig = taskConfig

        self._eventService = zope.component.queryUtility(IEventService)
        self._dataService = zope.component.queryUtility(IDataService)
        self._preferences = zope.component.queryUtility(
            ICollectorPreferences, 'zenexample')

        # All of these properties are required to implement the IScheduledTask
        # interface.
        self.name = taskName
        self.configId = deviceId
        self.interval = interval
        self.state = TaskStates.STATE_IDLE

    # doTask is where the collector logic should go. It is also required to
    # implement the IScheduledTask interface. It will be called directly by the
    # framework when it's this task's turn to run.
    def doTask(self):
        # This method must return a deferred because the collector framework
        # is asynchronous.
        d = defer.Deferred()
        return d

    # cleanup is required to implement the IScheduledTask interface.
    def cleanup(self):
        pass


if __name__ == '__main__':
    myPreferences = ZenExamplePreferences()
    myTaskFactory = SimpleTaskFactory(ZenExampleTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)

    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
