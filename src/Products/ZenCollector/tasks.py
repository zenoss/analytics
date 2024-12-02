##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2010, 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import division

import logging
import random

from copy import copy

import six

import zope.component
import zope.interface

from Products.ZenUtils.observable import ObservableMixin
from Products.ZenUtils.Utils import readable_time

from .interfaces import IScheduledTaskFactory, ISubTaskSplitter, ITaskSplitter

log = logging.getLogger("zen.collector.tasks")


class BaseTask(ObservableMixin):
    """
    Convenience class that consolidates some shared code.
    """

    # By default, track when this task is 'late.'
    suppress_late = False

    def __init__(self, *args, **kwargs):
        super(BaseTask, self).__init__()

        # Store the original cycle interval so that we
        # can go back when an error condition is resolved.
        interval = kwargs.get("scheduleIntervalSeconds")
        if interval is not None:
            self._originalScheduleInterval = interval
        else:
            self._originalScheduleInterval = args[2]

    def cleanup(self):  # Required by interface
        pass

    def scheduled(self, scheduler):  # Required by interface
        pass

    def _delayNextCheck(self):
        """
        Rather than keep re-polling at the same periodicity to
        determine if the device's agent is responding or not,
        let this task back up in the queue.
        Add a random element to it so that we don't get the
        thundering herd effect.
        A maximum delay is used so that there is a bound on the
        length of times between checks.
        """
        # If it's not responding, don't poll it so often
        if self.interval != self._maxbackoffseconds:
            delay = _randomize_delay(self.interval)
            self.interval = min(self._maxbackoffseconds, self.interval + delay)
            log.debug(
                "Delaying next check for another %s",
                readable_time(self.interval),
            )

    def _returnToNormalSchedule(self, ignored=None):
        """
        Once a task is successful, reset the original cycle interval.
        The ignored kwarg is used so that the method can be called
        directly as a deferred callback.
        """
        if self.interval != self._originalScheduleInterval:
            self.interval = self._originalScheduleInterval
            log.debug(
                "Resetting next check back to %s seconds",
                self._originalScheduleInterval,
            )
        return ignored

    def chunk(self, lst, n):
        """
        Break lst into n-sized chunks
        """
        return [lst[i : i + n] for i in six.moves.range(0, len(lst), n)]


def _randomize_delay(interval):
    return random.randint(interval // 2, interval) * 2  # noqa: S311


@zope.interface.implementer(ITaskSplitter)
class NullTaskSplitter(object):
    """
    A task splitter that is used with a NullConfigService for
    situations where no configuration will be returned.
    """

    def splitConfiguration(self, configs):
        return {}


@zope.interface.implementer(ITaskSplitter)
class SimpleTaskSplitter(object):
    """
    A task splitter that creates a single scheduled task for an entire
    configuration.
    """

    def __init__(self, taskFactory):
        """
        Creates a new instance of DeviceTaskSpliter.

        @param taskClass the class to use when creating new tasks
        @type any Python class
        """
        if not IScheduledTaskFactory.providedBy(taskFactory):
            raise TypeError("taskFactory must implement IScheduledTaskFactory")
        else:
            self._taskFactory = taskFactory

    def _newTask(self, name, configId, interval, config):
        """
        Handle the dirty work of creating a task
        """
        self._taskFactory.reset()
        self._taskFactory.name = name
        self._taskFactory.configId = configId
        self._taskFactory.interval = interval
        self._taskFactory.config = config

        return self._taskFactory.build()

    def splitConfiguration(self, configs):
        tasks = {}
        for config in configs:
            log.debug("splitting config %r", config)

            configId = config.configId
            interval = config.configCycleInterval
            tasks[configId] = self._newTask(
                configId, configId, interval, config
            )
        return tasks


@zope.interface.implementer(ISubTaskSplitter)
class SubConfigurationTaskSplitter(SimpleTaskSplitter):
    """
    A task splitter that creates a single scheduled task by
    device, cycletime and other criteria.
    """

    subconfigName = "datasources"

    def makeConfigKey(self, config, subconfig):
        raise NotImplementedError("Required method not implemented")

    def _splitSubConfiguration(self, config):
        subconfigs = {}
        for subconfig in getattr(config, self.subconfigName):
            key = self.makeConfigKey(config, subconfig)
            subconfigList = subconfigs.setdefault(key, [])
            subconfigList.append(subconfig)
        return subconfigs

    def splitConfiguration(self, configs):
        # This name required by ITaskSplitter interface
        tasks = {}
        for config in configs:
            log.debug("Splitting config %s", config)

            # Group all of the subtasks under the same configId
            # so that updates clean up any previous tasks
            # (including renames)
            configId = config.configId

            subconfigs = self._splitSubConfiguration(config)
            for key, subconfigGroup in subconfigs.items():
                name = " ".join(map(str, key))
                interval = key[1]

                configCopy = copy(config)
                setattr(configCopy, self.subconfigName, subconfigGroup)

                tasks[name] = self._newTask(
                    name, configId, interval, configCopy
                )
        return tasks


@zope.interface.implementer(IScheduledTaskFactory)
class SimpleTaskFactory(object):
    """
    A simple task factory that creates a scheduled task using the provided
    task class and the minimum attributes needed for a task.
    """

    def __init__(self, taskClass):
        """
        Create a new task factory instance using the specified task class when
        creating new task objects. The taskClass must provide an __init__
        method with the following signature:

        def __init__(self, name, configId, interval, config):

        @param taskClass: the class to use when creating new task objects
        @type taskClass: a Python class object
        """
        self._taskClass = taskClass
        self.reset()

    def build(self):
        return self._taskClass(
            self.name, self.configId, self.interval, self.config
        )

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None


class TaskStates(object):
    STATE_IDLE = "IDLE"
    STATE_CONNECTING = "CONNECTING"
    STATE_RUNNING = "RUNNING"
    STATE_WAITING = "WAITING"
    STATE_QUEUED = "QUEUED"
    STATE_PAUSED = "PAUSED"
    STATE_CLEANING = "CLEANING"
    STATE_COMPLETED = "COMPLETED"
    STATE_SHUTDOWN = "SHUTDOWN"
