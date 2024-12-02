##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenModel.ThresholdInstance import MetricThresholdInstance

__doc__= """MinMaxThreshold
Make threshold comparisons dynamic by using TALES expresssions,
rather than just number bounds checking.
"""

from AccessControl import Permissions

from AccessControl.class_init import InitializeClass
from ThresholdClass import ThresholdClass
from ThresholdInstance import ThresholdContext
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Perf_Snmp
from Products.ZenUtils.ZenTales import talesEval, talesEvalStr
from Products.ZenEvents.Exceptions import pythonThresholdException, \
        rpnThresholdException

import logging
log = logging.getLogger('zen.MinMaxCheck')

from Products.ZenUtils.Utils import unused, nanToNone

# Note:  this import is for backwards compatibility.
# Import Products.ZenRRD.utils.rpneval directy.
from Products.ZenRRD.utils import rpneval

NaN = float('nan')

class MinMaxThreshold(ThresholdClass):
    """
    Threshold class that can evaluate RPNs and Python expressions
    """

    minval = ""
    maxval = ""
    eventClass = Perf_Snmp
    severity = 3
    escalateCount = 0
    description = ''
    explanation = ''
    resolution = ''

    _properties = ThresholdClass._properties + (
        {'id':'minval',        'type':'string',  'mode':'w'},
        {'id':'maxval',        'type':'string',  'mode':'w'},
        {'id':'escalateCount', 'type':'int',     'mode':'w'},
        {'id': 'description', 'type': 'string', 'mode': 'rw'},
        {'id': 'explanation', 'type': 'string', 'mode': 'rw'},
        {'id': 'resolution', 'type': 'string', 'mode': 'rw'},
        )

    factory_type_information = (
        {
        'immediate_view' : 'editRRDThreshold',
        'actions'        :
        (
        { 'id'            : 'edit'
          , 'name'          : 'Min/Max Threshold'
          , 'action'        : 'editRRDThreshold'
          , 'permissions'   : ( Permissions.view, )
          },
        )
        },
        )

    def createThresholdInstance(self, context):
        """
        Return the config used by the collector to process min/max
        thresholds. (id, minval, maxval, severity, escalateCount)
        """
        mmt = MinMaxThresholdInstance(self.id,
                                      ThresholdContext(context),
                                      self.dsnames,
                                      minval=self.getMinval(context),
                                      maxval=self.getMaxval(context),
                                      eventClass=self.eventClass,
                                      severity=self.getSeverity(context),
                                      escalateCount=self.getEscalateCount(context),
                                      eventFields=self.getEventFields(context),
              )
        return mmt

    def getMinval(self, context):
        """
        Build the min value for this threshold.
        """
        return self.evaluateDataSourceExpression(context, 'minval', 'minimum value')

    def getMaxval(self, context):
        """
        Build the max value for this threshold.
        """
        return self.evaluateDataSourceExpression(context, 'maxval', 'maximum value')

    def getSeverity(self, context):
        """
        Build the severity for this threshold.
        """
        return self.severity

    def getEscalateCount(self, context):
        """
        Build the escalation count for this threshold.
        """
        return self.escalateCount

    def evaluateDataSourceExpression(self, context, propName, readablePropName):
        """
        Return back a sane value from evaluation of an expression.

        @paramter context: device or component object
        @type context: device or component object
        @paramter propName: name of the threshold property to evaluate
        @type propName: string
        @paramter readablePropName: property name for displaying in error messages
        @type readablePropName: string
        @returns: numeric
        @rtype: numeric
        """
        value = getattr(self, propName, None)
        if value:
            try:
                express = "python:%s" % value
                evaluated = talesEval(express, context)
                value = evaluated
            except Exception:
                nodeName = context.getNodeName()
                if nodeName == 'Device':
                    location = '{} of Device {}'.format(self.dsnames, context.id)
                else:
                    location = '{} of {} {} in Device {}'.format(self.dsnames, nodeName, context.id, context.device().id)

                msg= "User-supplied Python expression (%s) for %s caused error: %s" % (
                           value, readablePropName, location)
                log.error(msg)
                raise pythonThresholdException(msg)
                value = None
        return nanToNone(value)

    def getEventFields(self, context):
        """
        Add these fields to any resulting threshold event generated on the daemon.

        @paramter context: device or component object
        @type context: device or component object
        @returns: static event fields + values
        @rtype: dictionary
        """
        fields = {}
        for key in ('description', 'explanation', 'resolution'):
            value = getattr(self, key, None)
            if value:
                fields[key] = talesEvalStr(value, context)
        return fields


InitializeClass(MinMaxThreshold)
MinMaxThresholdClass = MinMaxThreshold


class MinMaxThresholdInstance(MetricThresholdInstance):
    # Not strictly necessary, but helps when restoring instances from
    # pickle files that were not constructed with a count member.
    count = {}

    def __init__(self, id, context, dpNames,
                 minval, maxval, eventClass, severity, escalateCount,
                 eventFields={}):
        MetricThresholdInstance.__init__(self, id, context, dpNames, eventClass, severity)
        self.count = {}
        self.minimum = minval if minval != '' else None
        self.maximum = maxval if maxval != '' else None
        self.escalateCount = escalateCount
        self.eventFields = eventFields

    def countKey(self, dp):
        return ':'.join(self.context().key()) + ':' + dp

    def getCount(self, dp):
        countKey = self.countKey(dp)
        if not countKey in self.count:
            return None
        return self.count[countKey]

    def incrementCount(self, dp):
        countKey = self.countKey(dp)
        if not countKey in self.count:
            self.resetCount(dp)
        self.count[countKey] += 1
        return self.count[countKey]

    def resetCount(self, dp):
        self.count[self.countKey(dp)] = 0

    def checkRange(self, dp, value):
        'Check the value for min/max thresholds'
        log.debug("Checking %s %s against min %s and max %s",
                  dp, value, self.minimum, self.maximum)
        if value is None:
            return []
        if isinstance(value, basestring):
            value = float(value)

        # Check the boundaries
        minbounds = self.minimum is None or value >= self.minimum
        maxbounds = self.maximum is None or value <= self.maximum
        outbounds = None not in (self.minimum, self.maximum) and \
                    self.minimum > self.maximum

        thresh = None
        how = None

        if outbounds:
            if not maxbounds and not minbounds:
                thresh = self.maximum
                how = 'violated'
        else:
            if not maxbounds:
                thresh = self.maximum
                how = 'exceeded'
            elif not minbounds:
                thresh = self.minimum
                how = 'not met'

        if thresh is not None:
            severity = self.severity
            count = self.incrementCount(dp)
            if self.escalateCount and count >= self.escalateCount:
                severity = min(severity + 1, 5)
            summary = 'threshold of %s %s: current value %f' % (
                self.name(), how, float(value))
            evtdict = self._create_event_dict(value, summary, severity, how)
            if self.escalateCount:
                evtdict['escalation_count'] = count
            return self.processEvent(evtdict)
        else:
            summary = 'threshold of %s restored: current value %f' % (
                self.name(), value)
            self.resetCount(dp)
            return self.processClearEvent(self._create_event_dict(value, summary, Event.Clear))

    def _create_event_dict(self, current, summary, severity, how=None):
        event_dict = dict(device=self.context().deviceName,
                          summary=summary,
                          eventKey=self.id,
                          eventClass=self.eventClass,
                          component=self.context().componentName,
                          min=self.minimum,
                          max=self.maximum,
                          current=current,
                          severity=severity)
        deviceUrl = getattr(self.context(), "deviceUrl", None)
        if deviceUrl is not None:
            event_dict["zenoss.device.url"] = deviceUrl
        devicePath = getattr(self.context(), "devicePath", None)
        if devicePath is not None:
            event_dict["zenoss.device.path"] = devicePath
        if how is not None:
            event_dict['how'] = how
        event_dict.update(self.eventFields)
        return event_dict

    def processEvent(self, evt):
        """
        When a threshold condition is violated, pre-process it for (possibly) nicer
        formatting or more complicated logic.

        @paramater evt: event
        @type evt: dictionary
        @rtype: list of dictionaries
        """
        return [evt]

    def processClearEvent(self, evt):
        """
        When a threshold condition is restored, pre-process it for (possibly) nicer
        formatting or more complicated logic.

        @paramater evt: event
        @type evt: dictionary
        @rtype: list of dictionaries
        """
        return [evt]

    def raiseRPNExc( self ):
        """
        Raise an RPN exception, taking care to log all details.
        """
        msg= "The following RPN exception is from user-supplied code."
        log.exception( msg )
        raise rpnThresholdException(msg)

    def getGraphValues(self, relatedGps, context):
        """
        Returns the values that we want to include for the
        visualization of this threshold. For a minmax we simply
        display lines representing the minval and maxval.
        """
        minval = self.minimum
        if minval is None or minval == '':
            minval = NaN
        maxval = self.maximum
        if maxval is None or maxval == '':
            maxval = NaN
        if not self.dataPointNames:
            return []
        gp = relatedGps[self.dataPointNames[0]]

        # Attempt any RPN expressions
        rpn = getattr(gp, 'rpn', None)
        if rpn:
            try:
                rpn = talesEvalStr(rpn, context)
            except Exception as e:
                log.exception(e)
                self.raiseRPNExc()
                return []

            try:
                if minval is not NaN:
                    minval = rpneval(minval, rpn)
            except Exception:
                minval= 0
                self.raiseRPNExc()

            try:
                if maxval is not NaN:
                    maxval = rpneval(maxval, rpn)
            except Exception:
                maxval= 0
                self.raiseRPNExc()

        minval = nanToNone(minval)
        maxval = nanToNone(maxval)
        return [minval, maxval]

    def getGraphElements(self, template, context, gopts, namespace, color,
                         legend, relatedGps):
        """
        Deprecated
        Produce a visual indication on the graph of where the
        threshold applies."""
        pass

    def getNames(self, relatedGps):
        names = sorted(set(x.split('_', 1)[1] for x in self.dataPointNames))
        return ', '.join(names)

    def setPower(self, number):
        powers = ("k", "M", "G")
        if number < 1000: return number
        for power in powers:
            number = number / 1000.0
            if number < 1000:
                return "%0.2f%s" % (number, power)
        return "%.2f%s" % (number, powers[-1])

    def _checkImpl(self, dataPoint, value):
        return self.checkRange(dataPoint, value)

from twisted.spread import pb
pb.setUnjellyableForClass(MinMaxThresholdInstance, MinMaxThresholdInstance)
