##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import six

from zope.configuration.fields import GlobalObject
from zope.interface import Interface
from zope.schema import TextLine


class IEventPluginDirective(Interface):
    """
    Registers an event plugin as a named utility.
    """

    plugin = GlobalObject(
        title=six.u("Plugin"),
        description=six.u("The class of the plugin to register"),
    )


class IPreEventPluginDirective(IEventPluginDirective):
    """
    Registers an event plugin as a named utility.
    """


class IPostEventPluginDirective(IEventPluginDirective):
    """
    Registers an event plugin as a named utility.
    """


class IEventIdentifierPluginDirective(IEventPluginDirective):
    """
    Registers an event identifier plugin as a named utility
    """

    name = TextLine(
        title=six.u("Name"),
        description=six.u(
            "The name of the event identifier plugin to register"
        ),
        required=False,
    )
