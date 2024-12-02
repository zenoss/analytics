##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenModel.Device import manage_createDevice
from Products.ZenModel.MetricMixin import MetricMixin


def attributeAsRRDValue(rrdView, id, **args):
    return getattr(rrdView, id)


class replaceGetRRDValue:
    def __init__(self, newMethod):
        self._newMethod = newMethod

    def __call__(self, fn):
        def wrappedFunction(*args):
            oldMethod = MetricMixin.getRRDValue
            MetricMixin.getRRDValue = self._newMethod
            try:
                return fn(*args)
            finally:
                MetricMixin.getRRDValue = oldMethod

        return wrappedFunction


def createTestDevice(
    dmd, deviceId, propertyMap={}, deviceClass="/Devices/Server"
):
    dev = manage_createDevice(dmd, deviceId, deviceClass)
    for key, value in propertyMap.iteritems():
        if hasattr(dev, key):
            setattr(dev, key, value)
    return dev


def getDeviceIdFromRecord(record):
    return record.values["device"].id


def getComponentIdFromRecord(record):
    return record.values["component"].id


def assertRecordIsCorrect(test, record, values):
    for key, value in values.iteritems():
        test.assert_(key in record.values)
        test.assertEquals(value, record[key])
