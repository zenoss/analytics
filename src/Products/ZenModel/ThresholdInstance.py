##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.spread import pb

from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.Utils import unused

log = logging.getLogger("zen.ThresholdInstance")


class ThresholdContext(pb.Copyable, pb.RemoteCopy):
    """Remember all the little details about a specific data point
    within a context.  This is useful for error messages and path
    information in the collectors.  It's a copy of the key bits of
    information from the Model."""

    def __init__(self, context):
        self.metricMetaData = {}
        if isinstance(context, MonitorClass):
            self.deviceName = "{ctx.id} hub".format(ctx=context)
            self.componentName = ""
            self.deviceUrl = (
                "zport/dmd/Monitors/Hub/{ctx.id}/viewHubPerformance"
            ).format(ctx=context)
            self.devicePath = "Monitors/Hub/{ctx.id}".format(ctx=context)
            self._contextKey = "/".join(("Daemons", context.id))

        elif isinstance(context, PerformanceConf):
            self.deviceName = "{ctx.id} collector".format(ctx=context)
            self.componentName = ""
            self.deviceUrl = (
                "zport/dmd/Monitors/Performance/{ctx.id}/viewDaemonPerformance"
            ).format(ctx=context)
            self.devicePath = "Monitors/Performance/{ctx.id}".format(
                ctx=context
            )
            self._contextKey = "/".join(("Daemons", context.id))

        else:
            self.deviceName = context.device().id
            self.componentName = context.id
            if self.componentName == self.deviceName:
                self.componentName = ""
            self._contextKey = context.getUUID()
            self.metricMetaData = context.getMetricMetadata()

        self._contextUid = context.getPrimaryId()

    def key(self):
        "Unique data that refers this context"
        return self.deviceName, self.componentName

    @property
    def contextUid(self):
        """
        Uid of the context
        @return: str
        """
        return self._contextUid

    @property
    def contextKey(self):
        """
        Unique id specific to the context
        @return: str
        """
        return self._contextKey

    @deprecated
    def fileKey(self, dataPoint):
        "Unique base filename for this context and given dataPoint"
        raise NotImplementedError()
        # return os.path.join(self.rrdPath, dataPoint)


pb.setUnjellyableForClass(ThresholdContext, ThresholdContext)


class ThresholdInstance(pb.Copyable, pb.RemoteCopy):
    """A ThresholdInstance is a threshold to be evaluated in a
    collector within a given context."""

    # count is unknown if None
    count = None

    def name(self):
        "return the name of this threshold (from the ThresholdClass)"

    def context(self):
        "Return the ThresholdContext for this ThresholdInstance"

    def key(self):
        "Unique data that refers to this object within a collector"
        return self.name(), self.context().key()

    def dataPoints(self):
        "Returns the names of the datapoints used to compute the threshold"

    def checkValue(self, dataPoint, timestamp, value):
        """
        Check if the value violates the threshold.

        @param dataPoint: datapoint definition
        @param timestamp: time of data collection
        @param value: value of the datapoint
        @return: sequence of Events
        """
        return self.checkRaw(dataPoint, timestamp, value)

    @deprecated
    def check(self, dataPoints):
        """The given datapoints have been updated, so re-evaluate.
        returns events or an empty sequence"""
        raise NotImplementedError()

    @deprecated
    def checkRaw(self, dataPoint, timeOf, value):
        """A new datapoint has been collected, use the given _raw_
        value to re-evalue the threshold.
        returns a sequence of events.
        """
        raise NotImplementedError()

    def getGraphElements(
        self, template, context, gopts, namespace, color, legend, relatedGps
    ):
        """Produce a visual indication on the graph of where the
        threshold applies."""
        unused(template, context, gopts, namespace, color, legend, relatedGps)
        return []


pb.setUnjellyableForClass(ThresholdInstance, ThresholdInstance)


class RRDThresholdInstance(ThresholdInstance):
    """
    Deprecated
    """


pb.setUnjellyableForClass(RRDThresholdInstance, RRDThresholdInstance)


class MetricThresholdInstance(ThresholdInstance):
    def __init__(self, id, context, dpNames, eventClass, severity):
        self._context = context
        self.id = id
        self.eventClass = eventClass
        self.severity = severity
        self.dataPointNames = dpNames

    def name(self):
        "return the name of this threshold (from the ThresholdClass)"
        return self.id

    def context(self):
        "Return an identifying context (device, or device and component)"
        return self._context

    def dataPoints(self):
        "Returns the names of the datapoints used to compute the threshold"
        return self.dataPointNames

    def checkValue(self, dataPoint, timestamp, value):
        return self._checkImpl(dataPoint, value)

    def _checkImpl(self, dataPoint, value):
        """

        Method used to check computed value against threshold

        @param dataPoint:
        @param value:
        @return:
        """
        raise NotImplementedError()


pb.setUnjellyableForClass(MetricThresholdInstance, MetricThresholdInstance)
