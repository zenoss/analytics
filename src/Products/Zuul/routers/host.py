##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging

from Products import Zuul
from Products.Zuul.routers import DirectRouter
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.interfaces import IInfo

log = logging.getLogger('zen.ApplicationRouter')


class HostRouter(DirectRouter):
    """
    """

    def _getFacade(self):
        return Zuul.getFacade('hosts', self.context)

    def getAllHosts(self):
        """
        Returns a list of host identifiers.
        @rtype: DirectResponse
        @return:  B{Properties}:
             - data: ([String]) List of hosts identifiers
        """
        hosts = self._getFacade().query()
        nodes = dict((host.id, host) for host in hosts)
        return DirectResponse.succeed(data=Zuul.marshal(nodes))