##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from datetime import datetime
from zope.interface import implementer
from Products.Zuul.interfaces import IApplicationInfo, IApplicationConfigurationInfo
from Products.Zuul.decorators import info
from Products.ZenUtils.application import ApplicationState

@implementer(IApplicationInfo)
class ApplicationInfo(object):
    """
    Info object for the applications returned from the control
    plane.
    """

    def __init__(self, app):
        """
        Initialize an instance of ApplicationInfo.

        :param IApplication application: The application.
        """
        self._object = app
        self._children = []

    @property
    def id(self):
        return self._object.id

    uid = id

    @property
    def name(self):
        return self._object.name

    text = name

    @property
    def hostId(self):
        return self._object.hostId

    @property
    def type(self):
        return "daemon"

    @property
    def description(self):
        return self._object.description

    qtip = description

    @property
    def autostart(self):
        return self._object.autostart

    @property
    def isRestarting(self):
        return self._object.state == ApplicationState.RESTARTING

    @property
    def uptime(self):
        started = self._object.startedAt
        if started:
            return str(datetime.today() - started)

    @property
    def state(self):
        return str(self._object.state)

    @property
    def leaf(self):
        return len(self.children) == 0

    def addChild(self, child):
        self._children.append(child)

    @property
    def children(self):
        return self._children

    @property
    @info
    def configFiles(self):
        return self._object.configurations

    def getConfigFileByFilename(self, filename):
        for configFile in self.configFiles:
            if configFile.filename == filename:
                return configFile
        # unable to find a config file by that name
        return None


@implementer(IApplicationConfigurationInfo)
class ApplicationConfigurationInfo(object):
    def __init__(self, config):
        """
        Initialize an instance of ApplicationInfo.

        :param IApplication application: The application.
        """
        self._object = config

    @property
    def filename(self):
        return self._object.filename

    @property
    def content(self):
        return self._object.content

    @content.setter
    def content(self, content):
        self._object.content = content
