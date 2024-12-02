##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from math import isnan
from zope.interface import implements
from Products.Zuul.interfaces import IFanInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class FanInfo(ComponentInfo):
    implements(IFanInfo)

    dataPointsToFetch = ['rpm']
    state = ProxyProperty('state')
    type = ProxyProperty('type')

    @property
    def rpm(self):
        rpm = self.getFetchedDataPoint('rpm')
        if rpm is not None and not isnan(rpm):
            rpm = long(rpm)
        return rpm
