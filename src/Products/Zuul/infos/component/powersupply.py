##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IPowerSupplyInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class PowerSupplyInfo(ComponentInfo):
    implements(IPowerSupplyInfo)

    dataPointsToFetch = ['millivolts']

    watts = ProxyProperty('watts')
    type = ProxyProperty('type')
    state = ProxyProperty('state')

    @property
    def millivolts(self):
        millivolts = self.getFetchedDataPoint('millivolts')
        if millivolts is not None:
            millivolts = long(millivolts)
        return millivolts
