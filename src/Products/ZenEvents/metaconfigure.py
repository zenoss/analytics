##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.zcml import utility

from .interfaces import (
    IEventIdentifierPlugin,
    IPostEventPlugin,
    IPreEventPlugin,
)


def preEventPlugin(_context, plugin, name=None):
    _eventPlugin(_context, plugin, IPreEventPlugin, name)


def postEventPlugin(_context, plugin, name=None):
    _eventPlugin(_context, plugin, IPostEventPlugin, name)


def eventIdentifierPlugin(_context, plugin, name=None):
    if name is None:
        name = ".".join((plugin.__module__, plugin.__name__))
    utility(
        _context, name=name, factory=plugin, provides=IEventIdentifierPlugin
    )


def _eventPlugin(_context, plugin, pluginInterface, name=None):
    if name is None:
        name = ".".join((plugin.__module__, plugin.__name__))
    utility(_context, name=name, factory=plugin, provides=pluginInterface)
