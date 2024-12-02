##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from AccessControl.class_init import InitializeClass
from twisted.spread import pb
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_INFO

from Products.ZenEvents.ZenEventClasses import Status_Perf
from Products.ZenUtils import Map

from .ThresholdClass import ThresholdClass
from .ThresholdInstance import MetricThresholdInstance, ThresholdContext

log = logging.getLogger("zen.MinMaxCheck")

NaN = float("nan")


class ValueChangeThreshold(ThresholdClass):
    """
    Threshold that can watch changes in a value.
    """

    eventClass = Status_Perf
    severity = SEVERITY_INFO

    def createThresholdInstance(self, context):
        """
        Return the config used by the collector to process change thresholds.
        """
        mmt = ValueChangeThresholdInstance(
            self.id,
            ThresholdContext(context),
            self.dsnames,
            eventClass=self.eventClass,
            severity=self.severity,
        )
        return mmt


InitializeClass(ValueChangeThreshold)
ValueChangeThresholdClass = ValueChangeThreshold


class ValueChangeThresholdInstance(MetricThresholdInstance):
    """
    Threshold that emits an event when a value changes from its
    previous value. Does not send clear events.
    """

    lastValues = Map.Locked(Map.Timed({}, 60 * 60 * 24))  # 24-hour timeout

    def _checkImpl(self, dataPoint, value):
        dpKey = self._getDpKey(dataPoint)
        lastValue = ValueChangeThresholdInstance.lastValues.get(dpKey, None)
        # get also updates the access time, so only set if the value changes.
        if lastValue != value:
            # Update the value in the map.
            ValueChangeThresholdInstance.lastValues[dpKey] = value
            # .. Only create a change event if this isn't the first collection
            if lastValue is not None:
                event = dict(
                    device=self.context().deviceName,
                    summary="Value changed from %s to %s" % (lastValue, value),
                    eventKey=self.id,
                    eventClass=self.eventClass,
                    component=self.context().componentName,
                    current=value,
                    previous=lastValue,
                    severity=self.severity,
                )
                return (event,)
        return tuple()

    def _getDpKey(self, dp):
        return ":".join(self.context().key()) + ":" + dp

    def getGraphValues(self, relatedGps, context):
        # currently, no visualization implemented for this threshold type
        return ()


pb.setUnjellyableForClass(
    ValueChangeThresholdInstance, ValueChangeThresholdInstance
)
