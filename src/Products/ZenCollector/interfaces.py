##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import zope.interface

# IEventService imported here for ZenPack compability
from Products.ZenHub.interfaces import IEventService  # noqa: F401
from Products.ZenUtils.observable import IObservable


class ICollectorPreferences(zope.interface.Interface):
    """
    A collector should implement this interface on an object whose primary
    responsibility will be to store configuration information for the
    collector.  The configuration information from the Performance Collector
    Configuration will be fetched and stored in this object and then provided
    to the rest of the collector framework for monitoring use.
    """

    collectorName = zope.interface.Attribute(
        """
        The friendly name of the collector.
        """
    )

    configurationService = zope.interface.Attribute(
        """
        The name of the remote ZenHub service that provides configuration for
        this collector.
        """
    )

    cycleInterval = zope.interface.Attribute(
        """
        The interval, specified in seconds, that the collector daemon will
        update performance statistics for itself, rather than any tasks.
        """
    )

    configCycleInterval = zope.interface.Attribute(
        """
        The interval, specified in minutes, that the collector's configuration
        will be updated from the ZenHub service.
        """
    )

    options = zope.interface.Attribute(
        """
        An attribute that will receive all command-line options parsed by the
        framework (incl. standard options and additional options defined by the
        buildOptions method).
        """
    )

    maxTasks = zope.interface.Attribute(
        """
        The max number of IScheduledTasks to be run at once
        """
    )

    def buildOptions(parser):
        """
        Called by the framework during initial startup to allow the collector
        to define any additional command-line options available to this
        collector.
        """

    def postStartup():
        """
        Called by the framework after initial startup has completed but before
        any active processing begins. Allows the configuration to perform any
        additional initialization that may be necessary after the collector has
        started.
        """

    def postStartupTasks():
        """
        Called by the framework after the preferences from zenhub have been
        received.  Configuration tasks may be started before these tasks are
        started.
        It is expected that if this optional method is provided that the result
        is an array of tasks.
        """


class ICollector(zope.interface.Interface):
    """
    A collector must use or implement a class that provides this interface.
    This object acts as the overall collector controller.

    Assumptions on a collector's behavior are:
    1. A collector keeps track of its own performance statistics.
    2. A collector interfaces with the rest of Zenoss using the ZenHub sevice
       and remote service proxies.
    """

    def getRemoteConfigServiceProxy():
        """
        Retrieve the remote configuration service proxy class. A collector
        should have retrieved the configuration service proxy based upon the
        collector's ICollectorPreferences implementation.
        @return a proxy object for the remote configuration service
        """


class IConfigurationProxy(zope.interface.Interface):
    """
    An implementation of the IConfigurationProxy is responsible for retrieving
    the configuration for a collector.
    """

    def getPropertyItems():
        """
        Retrieve the collector's property items.

        @return: properties for this collector
        @rtype: either a dict or a Deferred
        """

    def getThresholdClasses():
        """
        Retrieve the collector's required threshold classes.

        @return: the names of all the collector threshold classes to loaded
        @rtype: an iterable set of strings containing Python class names
        """

    def getThresholds():
        """
        Retrieve the collector's threshold definitions.

        @return: the threshold definitions
        @rtype: an iterable set of threshold definitions
        """

    def getConfigProxies(configIds=None):
        """
        Called by the framework whenever the configuration for this collector
        should be retrieved.

        @param configIds: specific config Ids to be configured
        @type configIds: an iterable
        @return: a twisted Deferred, optional in case the configure operation
                takes a considerable amount of time
        @rtype: twisted.internet.defer.Deferred
        """


class IScheduler(zope.interface.Interface):
    """
    A service that provides execution scheduling for objects implementing the
    IScheduledTask interface.
    """

    maxTasks = zope.interface.Attribute(
        """
    Max tasks the scheduler should run at once; unlimited if None
    """
    )

    def addTask(newTask, callback=None, now=False):
        """
        Add a new IScheduledTask to the scheduler for execution.
        @param newTask: the new task to schedule
        @type newTask: IScheduledTask
        @param callback: a callback to be notified each time the task completes
        @type callback: a Python callable
        @param now: if true schedule the task to run as soon as possible; by
        default the start time of tasks will be staggered
        @type now: boolean
        """

    def removeTasks(taskNames):
        """
        Remove tasks from scheduler.
        @param taskNames: a list of task names to remove
        @type: taskNames: list(string)
        """

    def removeTasksForConfig(configId):
        """
        Remove all tasks associated with the specified identifier.
        @param configId: the identifier to search for
        @type configId: string
        """

    def pauseTasksForConfig(configId):
        """
        Pauses, but does not stop, all tasks associated with the provided
        configuration identifier.

        @param configId: the identifier to search for
        @type configId: string
        """

    def resumeTasksForConfig(configId):
        """
        Resumes all paused asks associated with the provided configuration
        identifier.

        @param configId: the identifier to search for
        @type configId: string
        """

    def displayStatistics(verbose):
        """
        Displays statistics for the scheduler.

        @param verbose: if True, display extremely detailed statistics
        @type verbose: boolean
        """


class IScheduledTask(IObservable):
    """
    A task that has a periodic interval for scheduling.
    """

    name = zope.interface.Attribute(
        """
        A unique identifier for this task. Often this will simply be a config
        Id, but it may include component name or other identifier. A collector
        should ensure that its tasks are created with unique identifiers.
        """
    )

    configId = zope.interface.Attribute(
        """
        The config id associated with this task.
        """
    )

    interval = zope.interface.Attribute(
        """
        Execution frequency of this task, in seconds
        """
    )

    state = zope.interface.Attribute(
        """
        The current state of the task, i.e. IDLE, RUNNING, etc. States can be
        any string value a task requires, with a few limitations required by
        the default scheduler implementation. These limitations are:
        1) Tasks must enter the IDLE state immediately after being constructed.
        2) Tasks should not change their own state to any of the states in
           TaskStates on their own -the scheduler changes to these states as
           needed.
        """
    )

    suppress_late = zope.interface.Attribute(
        """
        Some tasks (e.g. config loaders) may not want to be counted as
        'late' to avoid muddying the meaning of our 'missedRuns' metrics
        on daemons.
        """
    )

    # childIds = zope.interface.Attribute(
    #     """
    #     Optional attribute: List of configIds of tasks that are
    #     associated with this task. When a task is removed any tasks
    #     with a configId in childIds will be removed as well.
    #     """
    # )

    def doTask():
        """
        Called whenever the task is scheduled to be executed by a scheduler.
        If a Deferred object is returned the task will not be considered
        finished until the deferred has completed and fired all callbacks.
        """

    def cleanup():
        """
        Called whenever the task is scheduled to be deleted by a scheduler.
        If a Deferred object is returned the task will not be considered
        finished with the cleanup until the deferred has completed and fired
        all callbacks.

        The framework will not call this method if the state is not IDLE,
        except during shutdowns.  If the framework is shutting down, the
        cleanup task will be required to handle this situation.

        Tasks should cleanup expensive resources in their implementation of
        this method and not rely upon the __del__ method being called to do
        so.
        """

    def scheduled(scheduler):
        """
        Called after a task has been scheduled.
        The scheduler instance is passed so that the scheduled task can
        manipulate it's (or another task's) schedule.
        """


class IPausingScheduledTask(IScheduledTask):
    """
    An IScheduledTask that needs to take action to pause and resume
    """

    def pause():
        """
        Called to pause a task.
        """

    def resume():
        """
        Called to resume a task.
        """


class IScheduledTaskFactory(zope.interface.Interface):
    """
    Collectors can provide their own task factories to build complex task
    objects that implement the IScheduledTask interface. The framework will use
    the task factory in the following way:

    factory.reset()
    factory.name = taskName
    factory.configId = taskConfigId
    ...
    newTask = factory.build()
    """

    name = zope.interface.Attribute(
        """
        A unique identifier for the new task.
        """
    )

    configId = zope.interface.Attribute(
        """
        The config id for the new task.
        """
    )

    interval = zope.interface.Attribute(
        """
        The execution frequency of this new task, in seconds.
        """
    )

    config = zope.interface.Attribute(
        """
        The detailed configuration that will be provided to the new task.
        """
    )

    def build():
        """
        Constructs a new object providing the IScheduledTask interface using
        the attributes currently set in the factory.
        @return: the new task object
        @rtype: any object providing IScheduledTask
        """

    def reset():
        """
        Resets all attributes in the factory to their default values so that
        a new task can be configured and built.
        """


class ITaskSplitter(zope.interface.Interface):
    """
    A service that splits up configuration into discrete tasks that can be
    scheduled.
    """

    def splitConfiguration(configuration):
        """Called whenever new configuration needs to be split into
        individually scheduled tasks."""


class ISubTaskSplitter(ITaskSplitter):
    """
    An object that accepts a configuration returned from a zenhub service
    and then creates scheduled tasks by device, cycletime and other criteria.
    """

    subconfigName = zope.interface.Attribute(
        """
        Name of the array containing the subconfiguration items.
        """
    )

    def makeConfigKey(config, subconfig):
        """
        Generate a tuple which determines how a configuration
        should be grouped into tasks.

        The result of this method is used to create the task name.
        The format of the result is:

        (config.id, interval, other_data)

        @parameter config: the device information
        @type config: DeviceProxy
        @parameter subconfig: a subconfiguration item
        @type subconfig: an object
        @return: a tuple that can be used to group datasources
        @rtype: tuple
        """


class IDataService(zope.interface.Interface):
    """
    A service that provides a mechanism to persist collected data.
    """

    def writeMetric(
        contextKey,
        metric,
        value,
        metricType,
        contextId,
        timestamp="N",
        min="U",
        max="U",
        threshEventData=None,
        deviceId=None,
        contextUUID=None,
        deviceUUID=None,
    ):
        """
        Write the value provided for the specified metric to Redis

        @param contextKey: The device or component the metric applies to.
            This is typically in the form a path.
        @type contextKey: str
        @param metric: The name of the metric, we expect it to be of the form
            datasource_datapoint.
        @type metric: str
        @param value: the value of the metric.
        @type value: float
        @param metricType: type of the metric (e.g. 'COUNTER', 'GAUGE',
            'DERIVE' etc)
        @type metricType: str
        @param contextId: used for the threshold events, the ID of the device.
        @type contextId: str
        @param timestamp: defaults to time.time() if not specified,
            the time the metric occurred.
        @type timestamp: float
        @param min: used in the derive the min value for the metric.
        @type min: float
        @param max: used in the derive the max value for the metric.
        @type max: float
        @param threshEventData: extra data put into threshold events.
        @type threshEventData: dict | None
        @param deviceId: the id of the device for this metric.
        @type deviceId: str
        @param contextUUID: The device/component UUID value
        @type contextUUID: str
        @param deviceUUID: The device UUID value
        @type deviceUUID: str
        """

    def writeMetricWithMetadata(
        metric,
        value,
        metricType,
        timestamp="N",
        min="U",
        max="U",
        threshEventData=None,
        metadata=None,
    ):
        """
        Basically wraps the `writeMetric` method.  The `metadata` parameter
        must contain the following fields:

            contextKey : str
            contextId : str
            deviceId : str
            contextUUID : str
            deviceUUID : str

        These fields have the same meaning as in the `writeMetric` method.

        @param metric: The name of the metric, we expect it to be of the form
            datasource_datapoint.
        @type metric: str
        @param value: the value of the metric.
        @type value: float
        @param metricType: type of the metric (e.g. 'COUNTER', 'GAUGE',
            'DERIVE' etc)
        @type metricType: str
        @param timestamp: defaults to time.time() if not specified,
            the time the metric occurred.
        @type timestamp: float
        @param min: used in the derive the min value for the metric.
        @type min: float
        @param max: used in the derive the max value for the metric.
        @type max: float
        @param threshEventData: extra data put into threshold events.
        @type threshEventData: dict
        @param metadata: Contains contextual data about the metric.
        @type metadata: dict
        """

    def writeRRD(
        path,
        value,
        rrdType,
        rrdCommand=None,
        cycleTime=None,
        min="U",
        max="U",
        threshEventData=None,
        timestamp="N",
        allowStaleDatapoint=True,
    ):
        """
        Save the value provided in the command to the RRD file specified
        in path.

        If the RRD file does not exist, use the rrdType, rrdCommand, min and
        max parameters to create the file.

        @param path: name for a datapoint in a path
            (eg device/component/datasource_datapoint)
        @type path: string
        @param value: value to store into the RRD file
        @type value: number
        @param rrdType: RRD data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        @param rrdCommand: RRD file creation command
        @type rrdCommand: string
        @param cycleTime: length of a cycle
        @type cycleTime: number
        @param min: minimum value acceptable for this metric
        @type min: number
        @param max: maximum value acceptable for this metric
        @type max: number
        @param threshEventData: on threshold violation,
            update the event with this data.
        @type threshEventData: dictionary | None
        @param allowStaleDatapoint: attempt to write datapoint even if a
            newer datapoint has already been written.
        @type allowStaleDatapoint: boolean
        @return: the parameter value converted to a number
        @rtype: number or None
        """


class IFrameworkFactory(zope.interface.Interface):
    """
    An abstract factory object that allows the collector framework to be
    dynamically extended at an interface level.
    """

    def getConfigurationProxy():
        """
        Retrieve the framework's implementation of the IConfigurationProxy
        interface.
        """

    def getScheduler():
        """
        Retrieve the framework's implementation of the IScheduler interface.
        """

    def getConfigurationLoaderTask(*args, **kw):
        """
        Return an instance of the configuration loader task constructed
        from the provided arguments.
        """

    def getBuildOptions(parser):
        """
        Apply the framework's build options to the given parser object.
        """


class IConfigurationListener(zope.interface.Interface):
    """
    Notified of configuration life cycle events
    """

    def deleted(configurationId):
        """
        Called when a configuration is deleted from the collector
        """

    def added(configuration):
        """
        Called when a configuration is added to the collector
        """

    def updated(newConfiguration):
        """
        Called when a configuration is updated in collector
        """


class IStatistic(zope.interface.Interface):
    """
    A named statistical value.
    """

    name = zope.interface.Attribute(
        """
        Name of statistic.
        """
    )

    value = zope.interface.Attribute(
        """
        Current value of the statistic.
        """
    )

    type = zope.interface.Attribute(
        """
        The type of statistic; currently limited to COUNTER, GAUGE.
        """
    )


class IStatisticsService(zope.interface.Interface):
    """
    A statistical management service that keeps track of statistical objects
    and posts them periodically to the data service.
    """

    def addStatistic(name, type):
        """
        Adds a new statistic to the service. Throws an exception if the
        statistic already exists.
        @param name: the unique name of the statistic
        @type name: string
        @param type: the type of the counter, limited to COUNTER, GAUGE
        @type type: string
        """

    def getStatistic(name):
        """
        Retrieves the statistic object for the given name.
        @param name: the unique name of the statistic
        @type name: string
        @return: the statistic object for the given name
        @rtype: an object implementing IStatistic
        """


class IWorkerTaskFactory(IScheduledTaskFactory):
    """
    An IScheduledTaskFactory that accepts an ICollectorWorker type for
    delegation.
    """

    def setWorkerClass(iCollectorWorker):
        """
        Set up a worker type
        """

    def postInitialization():
        """
        Called after collecter daemon initialization for final taskFactory
        setup.
        """


class ICollectorWorker(zope.interface.Interface):
    """
    A worker that has the capability of collecting data.
    """

    def prepareToRun():
        """
        Pre-run initialization
        """

    def collect(device, taskConfig, *args):
        """
        Collect data for device
        """

    def disconnect(device):
        """
        Disconnect from target device
        """

    def stop():
        """
        Stop running
        """


class IWorkerExecutor(zope.interface.Interface):
    """
    A service that instantiates and executes a provided ICollectorWorker
    """

    def setWorkerClass(workerClass):
        """
        Set up a worker
        """

    def run():
        """
        run the provided worker
        """


class IConfigurationDispatchingFilter(zope.interface.Interface):
    def getFilter(options):
        """
        A function to get a filter function to filter the devices for which
        to generate configs. The returned filter function must be suitable
        for use with the 'filter' builtin. 'options' is a dictionary of
        potential control options for the filter.
        """
