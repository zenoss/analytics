##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import calendar
import time
import re
import json
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
log = logging.getLogger("zen.MetricMixin")

from Acquisition import aq_chain
from Products.ZenUtils import Map
from Products.ZenUtils.metrics import SEPARATOR_CHAR
from Products.ZenWidgets import messaging
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul import getFacade

CACHE_TIME = 60.

_cache = Map.Locked(Map.Timed({}, CACHE_TIME))


class MetricMixin(object):
    """
    Mixin to provide hooks to metric service management functions
    """

    def cacheValue(self, dsname, default = "Unknown"):
        """
        Cache metric values for up to CACHE_TIME(60) seconds.
        """
        cacheKey = self.getCacheKey(dsname)
        try:
            value = _cache[cacheKey]
        except KeyError:
            try:
                value = self.getRRDValue(dsname)
            except Exception as ex:
                value = None
                log.error('Unable to get RRD value for %s: %s', dsname, ex)
            _cache[cacheKey] = value

        if value is None or value == {}:
            return default
        return value

    # alias the method for back compat
    cacheRRDValue = cacheValue

    def getCacheKey(self, dsname):
        """
        Make sure we have a unique key for this cache entry depending on the dsname
        """
        return self.getUUID() + "-" + dsname

    def _getRRDDataPointsGen(self):
        for t in self.getRRDTemplates():
            for dp in t.getRRDDataPoints():
                yield dp

    def getRRDDataPoints(self):
        return list(self._getRRDDataPointsGen())

    def getRRDDataPoint(self, dpName):
        return next((dp for dp in self._getRRDDataPointsGen()
                                    if dp.name() == dpName), None)

    def getRRDValue(self, dsname, start=None, end=None, function="LAST",
                    format="%.2lf", extraRpn="", cf="AVERAGE"):
        """
        Return a single rrd value from its file using function.
        """
        dsnames = (dsname,)
        results = self.getRRDValues(
            dsnames, start, end, function, format, extraRpn, cf=cf)
        if results and dsname in results:
            return results[dsname]

    def getRRDValues(self, dsnames, start=None, end=None, function="LAST",
                     format="%.2lf", extraRpn="", cf="AVERAGE"):
        """
        Return a dict of key value pairs where dsnames are the keys.
        """
        try:
            fac = getFacade('metric', self.dmd)
            return fac.getValues(self, dsnames, start=start, end=end, format=format,
                                    extraRpn=extraRpn, cf=cf)
        except Exception:
            log.exception("Unable to collect metric values for %s", self.getPrimaryId())
        # couldn't get any metrics return an empty dictionary
        return {}

    def getGraphObjects(self):
        """
        Returns GraphDefinition objects and contexts in a tuple for all the templates bound
        to this object.
        """
        graphs = []
        for template in self.getRRDTemplates():
            for g in template.getGraphDefs():
                graphs.append((g, self))
        return graphs

    def getGraphObject(self, graphId):
        return next((g for t in self.getRRDTemplates()
                                for g in t.getGraphDefs()
                                    if g.id == graphId),
                         None)

    def getDefaultGraphDefs(self, drange=None):
        """Backwards compatible layer for zenpacks. """
        log.warn('As of zenoss 5.x and above getDefaultGraphDefs is not supported, use getGraphObjects instead.')
        return []

    def getGraphDef(self, graphId):
        ''' Fetch a graph by id.  if not found return None
        '''
        return next((g for t in self.getRRDTemplates()
                                for g in t.getGraphDefs()
                                    if g.id == graphId),
                         None)

    def getRRDTemplateName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type

    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False

    def getRRDTemplates(self):
        templates = []
        defaultName = self.getRRDTemplateName()
        default = self.getRRDTemplateByName(defaultName)
        if not default:
            return []
        replacement = self.getRRDTemplateByName('{}-replacement'.format(defaultName))
        if replacement:
            templates.append(replacement)
        else:
            templates.append(default)
        addition = self.getRRDTemplateByName('{}-addition'.format(defaultName))
        if addition:
            templates.append(addition)
        return templates

    def getRRDTemplate(self):
        try:
            return self.getRRDTemplates()[0]
        except IndexError:
            return None

    def getRRDTemplateByName(self, name):
        "Return the template of the given name."
        try:
            return self._getOb(name)
        except AttributeError:
            pass
        for obj in aq_chain(self):
            try:
                return obj.rrdTemplates._getOb(name)
            except AttributeError:
                pass
        return None

    def getThresholds(self, templ):
        """Return a dictionary where keys are dsnames and values are thresholds.
        """
        result = {}
        for thresh in templ.thresholds():
            if not thresh.enabled: continue
            for dsname in thresh.dsnames:
                threshdef = result.setdefault(dsname, [])
                threshdef.append(thresh.getConfig(self))
        return result

    def rrdPath(self):
        """
        Overriding this method to return the uuid since that
        is what we want to store in the metric DB.
        """
        return json.dumps(self.getMetricMetadata(), sort_keys=True)

    def getResourceKey(self, d=None):
        """
        Formerly RRDView.GetRRDPath, this value is still used as the key for the
        device or component in OpenTSDB.
        """
        if d is None:
            d = self.device()
        if not d:
            return "Devices/" + self.id
        skip = len(d.getPrimaryPath()) - 1
        return 'Devices/' + '/'.join(self.getPrimaryPath()[skip:])

    def getMetricNameContext(self):
        """
        Used in conjuction with the 'contextMetric' property. If 'contexMetric' is True,
        this method will be called to get additional context for the metricname.
        """
        return self.id

    def contextMetric(self):
        """
        If true the metric name prefix will contain value returned by 'getMetricNameContext'
        """
        return False
    
    def getMetricMetadata(self, dev=None):
        if dev is None:
            dev = self.device()
            
        mdata = {
                'type': 'METRIC_DATA',
                'contextKey': self.getResourceKey(dev),
                'deviceId': dev.id,
                'contextId': self.id,
                'deviceUUID': dev.getUUID(),
                'contextUUID': self.getUUID()
                }

        if self.contextMetric():
            metricContext = self.getMetricNameContext()
            mdata['metricPrefix'] = '%s%s%s' % (dev.id, SEPARATOR_CHAR , metricContext)

        return mdata

    def getRRDContextData(self, context):
        return context

    def getThresholdInstances(self, dsType):
        from Products.ZenEvents.Exceptions import pythonThresholdException
        result = []
        for template in self.getRRDTemplates():
            # if the template refers to a data source name of the right type
            # include it
            names = set(dp.name() for ds in template.getRRDDataSources(dsType)
                                for dp in ds.datapoints())
            for threshold in template.thresholds():
                if not threshold.enabled: continue
                for ds in threshold.dsnames:
                    if ds in names:
                        try:
                            thresh = threshold.createThresholdInstance(self)
                            result.append(thresh)
                        except pythonThresholdException as ex:
                            log.warn(ex)
                            zem = self.primaryAq().getEventManager()
                            import socket
                            device = socket.gethostname()
                            path = template.absolute_url_path()
                            msg = \
"The threshold %s in template %s has caused an exception." % (threshold.id, path)
                            evt = dict(summary=str(ex), severity=3,
                                    component='zenhub', message=msg,
                                    dedupid='zenhub|' + str(ex),
                                    template=path,
                                    threshold=threshold.id,
                                    device=device, eventClass="/Status/Update",)
                            zem.sendEvent(evt)
                        break
        return result

    def makeLocalRRDTemplate(self, templateName=None, REQUEST=None):
        """
        Make a local copy of our RRDTemplate if one doesn't exist.
        """
        if templateName is None: templateName = self.getRRDTemplateName()
        if not self.isLocalName(templateName):
            ct = self.getRRDTemplateByName(templateName)._getCopy(self)
            ct.id = templateName
            self._setObject(ct.id, ct)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Template Created',
                'Local copy "%s" created.' % templateName
            )
            return self.callZenScreen(REQUEST)

    def removeLocalRRDTemplate(self, templateName=None, REQUEST=None):
        """
        Delete our local RRDTemplate if it exists.
        """
        if templateName is None: templateName = self.getRRDTemplateName()
        if self.isLocalName(templateName):
            self._delObject(templateName)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Template Removed',
                'Local copy "%s" removed.' % templateName
            )
            return self.callZenScreen(REQUEST)

    def getUUID(self):
        return IGlobalIdentifier(self).getGUID()

    def fetchMetrics(self, dpnames, cf, resolution, start, end="now",
                     returnSet="ALL"):
       """
       Query the server for metrics and return the response.
       """
       facade = getFacade('metric', self.dmd)
       return facade.queryServer(self, dpnames, cf=cf, start=start, end=end,
                                 downsample=resolution, returnSet=returnSet)

    def fetchRRDValues(self, dpnames, cf, resolution, start, end="now"):
        """
        Compat method for RRD. This returns a list of metrics.
        The output looks something like this
        $> pprint(obj.fetchRRDValues('dsname_dpname', 'AVERAGE', 300, 'end-1d', 'now'))
           ((1417452900, 1417539600, 300),
            ('ds0',),
          [(83.69137058,),
            (83.69137058,),
            (83.69137058,),
            ... would be more here ...
            (None,),
            (None,)])
        That maps to..
            ((start, end, resolution),
             ('ds0',),
            [(v1,),
             (v2,),
             (v3,)])
        To ensure backwards compatibility with RRD the following should be taken into account:
        The number of values has to be == (end-start) / resolution. None's will be filled in for the missing slots
        The expectation is that each value correspond to its time slot.
        There's no expectation that the passed resolution is the returned resolution.

        The start and end parameters can be specified as a UNIX
        timestamps or a subset of RRDtool AT-STYLE time specification. See http://oss.oetiker.ch/rrdtool/doc/rrdfetch.en.html

        You can also pass in OpenTSDB relative times, such as '1d-ago'.
        """
        results = []
        if isinstance(dpnames, basestring):
            dpnames = [dpnames]

        # parse start and end into unix timestamps
        start, end = self._rrdAtTimeToUnix(start, end)
        response = self.fetchMetrics(dpnames, cf=cf, resolution=resolution, start=start, end=end)

        values = response.get('results', [])
        firstRow = (response.get('startTimeActual'), response.get('endTimeActual'), resolution)
        secondRow = ('ds0',)

        for value in values:
            thirdRow = []
            if value:
                thirdRow = self._createRRDFetchResults(response.get('startTimeActual'), response.get('endTimeActual'), resolution, value)
            results.append((firstRow, secondRow, thirdRow))

        return results

    def fetchRRDValue(self, dpname, cf, resolution, start, end="now"):
        """
        Calls fetch RRDValue but returns the first result.
        """
        r = self.fetchRRDValues([dpname, ], cf, resolution, start, end=end)
        if r:
            return r[0]
        return None

    def _createRRDFetchResults(self, start, end, resolution, value):
        """
        Given a set of metrics returned from the metric server and the start, end and resolution
        this method returns a metric for each "step" or a None if one can't be found.

        Each entry in the buckets is a tuple of one item.
        """
        size = int((end - start) / resolution)

        # create a list of None's for the return value
        buckets = [(None,) for x in range(size)]
        currentTime = start
        if not value:
            return buckets

        # we are making the assumption we are only working with one datapoint
        # also that the return set is sorted sequentially
        try:
            values = value['datapoints']
        except KeyError:
            log.error("Unable to find datapoints from metric query results %s", value)
            return buckets

        for idx, _ in enumerate(buckets):
            if len(values) == 0 or currentTime > end:
                break
            # if we only have one left and are at a higher time then include the value
            # otherwise make sure our current time is somewhere between the next two steps to
            # include it.
            # This way the None's aren't pushed all the way to the end of the buckets
            if (len(values) == 1 and currentTime > values[0]['timestamp'] or \
                (len(values) > 1 and currentTime >= values[0]['timestamp'] and currentTime < values[1]['timestamp'])):
                buckets[idx] = (values[0]['value'],)
                values.pop(0)

            # move to the next bucket
            currentTime += resolution
        return buckets

    def _rrdAtTimeToUnix(self, start, end):
        """
        This is my best effort at parsing a sub-set of the "at" time of rrd to
        unix timestamps.
        This method will accept something of the following:
           now == current time
           -X['d' | 'm' | 's' | 'h'] // X is the number and d = day, m = minute etc
           The start time can be relative to the end by passing in end like
           end-1d // end minus one day
        """
        newEnd = newStart = None
        # find out end first
        if end == "now":
            newEnd = time.time()
        else:
            # if it is an int or an OpenTSDB style string then we can just
            # pass it to the metric facade
            if not isinstance(end, basestring) or 'ago' in end:
                newEnd = end
            else:
                newEnd = self._parseTime(end, time.time())
        if isinstance(start, basestring) and  "end-" in start:
            fromTime = newEnd
        else:
            fromTime = time.time()
        if not isinstance(start, basestring) or 'ago' in start:
            newStart = start
        else:
            newStart = self._parseTime(start.replace("end-", ""), fromTime)
        return newStart, newEnd

    def _parseTime(self, token, fromTime):
        dateMap = {
            'd': 'days',
            'm': 'minutes',
            's': 'seconds',
            'h': 'hours',
            'w': 'weeks',
            'y': 'years',
            'month': 'months'
        }
        numbers = re.findall(r'\d+', token)
        if len(numbers):
            numberPart = int(numbers[0])
        else:
            numberPart = 1
        characters = [x for x in token.replace("-", "") if x.isalpha()]
        timePart = characters[0]
        if numberPart < 25 and timePart == 'm':
            timePart = 'month'

        if not dateMap.get(timePart):
            raise ValueError("Unable to parse the time from input %s" % token)

        timePart = dateMap[timePart]
        args = {
            timePart: numberPart
        }
        delta = relativedelta(**args)
        fromDateTime = datetime.fromtimestamp(fromTime)
        newDate = fromDateTime - delta
        return calendar.timegm(newDate.utctimetuple())
