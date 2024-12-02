##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component import queryUtility
from zope.interface import implementer

from .config import ConfigurationLoaderTask, ConfigurationProxy
from .interfaces import IFrameworkFactory, ICollectorPreferences
from .scheduler import TaskScheduler


@implementer(IFrameworkFactory)
class CoreCollectorFrameworkFactory(object):
    def __init__(self):
        self.__configProxy = None
        self.__scheduler = None

    def getConfigurationProxy(self):
        if self.__configProxy is None:
            prefs = queryUtility(ICollectorPreferences)
            self.__configProxy = ConfigurationProxy(prefs)
        return self.__configProxy

    def getScheduler(self):
        if self.__scheduler is None:
            self.__scheduler = TaskScheduler.make()
        return self.__scheduler

    def getConfigurationLoaderTask(self):
        return ConfigurationLoaderTask

    def getFrameworkBuildOptions(self):
        return None
