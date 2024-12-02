##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component import getUtilitiesFor
from ..interfaces import IConfigurationDispatchingFilter


def getOptionsFilter(options):
    if options:
        name = options.get("configDispatch", "") if options else ""
        factories = dict(getUtilitiesFor(IConfigurationDispatchingFilter))
        factory = factories.get(name)
        if factory is None:
            factory = factories.get("")
        if factory is not None:
            devicefilter = factory.getFilter(options)
            if devicefilter:
                return devicefilter

    return _alwaysTrue


def _alwaysTrue(*args):
    return True
