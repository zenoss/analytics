##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from zope.component import getUtility
from zope.interface import implementer

from Products.ZenUtils.host import IHostManager
from Products.Zuul.interfaces.host import IHostFacade
from Products.Zuul.decorators import info

LOG = logging.getLogger("Zuul.facades")


@implementer(IHostFacade)
class HostFacade(object):
    """
    """
    
    def __init__(self, dataroot):
        """
        """
        self._dmd = dataroot
        self._svc = getUtility(IHostManager)

    @info
    def query(self):
        """
        Returns a sequence of application objects.
        """
        result = self._svc.query()

        if not result:
            return ()

        return tuple(result)