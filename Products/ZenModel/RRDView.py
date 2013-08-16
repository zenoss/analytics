##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time
import json
import logging
log = logging.getLogger("zen.RRDView")

from Acquisition import aq_chain
from Products.ZenUtils import Map
from Products.ZenWidgets import messaging
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenModel.ConfigurationError import ConfigurationError
from Products.Zuul import getFacade
CACHE_TIME = 60.

_cache = Map.Locked(Map.Timed({}, CACHE_TIME))




class RRDViewError(Exception): pass


class RRDView(object):
    """
    Mixin to provide hooks to RRD management functions
    """

    def cacheRRDValue(self, dsname, default = "Unknown"):
        """
        Cache RRD values for up to CACHE_TIME seconds.
        """
        # Notes:
        #  * _cache takes care of the time-limited-offer bits
        #  * rrdcached does cache results, but the first query
        #    could potentially cause a flush()
        #  * Remote collectors need this call to prevent extra
        #    calls across the network
        filename = self.getRRDFileName(dsname)
        try:
            value = _cache[filename]
        except KeyError:
            try:
                # Grab rrdcached value locally or from network
                value = self.getRRDValue(dsname)
            except Exception as ex:
                # Generally a remote collector issue
                # We'll cache this for a minute and then try again
                value = None
                log.error('Unable to get RRD value for %s: %s', dsname, ex)
            _cache[filename] = value
        
        return value if value is not None else default

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

    def _getRRDDataPointsGen(self):
        for t in self.getRRDTemplates():
            for dp in t.getRRDDataPoints():
                yield dp

    def getRRDDataPoints(self):
        return list(self._getRRDDataPointsGen())

    def getRRDDataPoint(self, dpName):
        return next((dp for dp in self._getRRDDataPointsGen() 
                                    if dp.name() == dpName), None)

    def fetchRRDValues(self, dpnames, cf, resolution, start, end=""):
        paths = [self.getRRDFileName(dpname) for dpname in dpnames]
        return self.device().getPerformanceServer().fetchValues(paths,
            cf, resolution, start, end)

    def fetchRRDValue(self, dpname, cf, resolution, start, end=""):
        r = self.fetchRRDValues([dpname,], cf, resolution, start, end=end)
        if r:
            return r[0]
        return None

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

    def getRRDSum(self, points, start=None, end=None, function="LAST"):
        "Return a sum of listed datapoints."

        try:
            if not start:
                start = time.time() - self.defaultDateRange
            if not end:
                end = time.time()
            gopts = []
            for name in points:
                dp = next((dp_ for dp_ in self._getRRDDataPointsGen() 
                                    if name in dp_.name()), None)
                if dp is None:
                    raise RRDViewError("Unable to find data point %s" % name)
                    
                filename = self.getRRDFileName(dp.name())
                rpn = str(dp.rpn)
                if rpn:
                    rpn = "," + rpn
                gopts.append("DEF:%s_r=%s:ds0:AVERAGE" % (name, filename))
                gopts.append("CDEF:%s=%s_r%s" % (name, name, rpn))
            gopts.append("CDEF:sum=%s%s" % (','.join(points),
                                             ',+'*(len(points)-1)))
            gopts.append("VDEF:agg=sum,%s" % function)
            gopts.append("PRINT:agg:%.2lf")
            gopts.append("--start=%d" % start)
            gopts.append("--end=%d" % end)
            perfServer = self.device().getPerformanceServer()
            if perfServer:
                vals = perfServer.performanceCustomSummary(gopts)
                if vals is None:
                    return None
                return float(vals[0])
        except Exception, ex:
            log.exception(ex)

    def getDefaultGraphDefs(self, drange=None):
        """get the default graph list for this object"""
        graphs = []
        for template in self.getRRDTemplates():
            for g in template.getGraphDefs():
                graph = {}
                graph['title'] = g.getId()
                try:
                    graph['url'] = self.getGraphDefUrl(g, drange, template)
                    graphs.append(graph)
                except ConfigurationError:
                    pass
        return graphs

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

    def getRRDFileName(self, dsname):
        """Look up an rrd file based on its data point name"""
        nm = next((p.name() for p in self._getRRDDataPointsGen() 
                            if p.name().endswith(dsname)), dsname)
        return '%s/%s' % (str(self.rrdPath()), nm)

    def getRRDNames(self):
        return []

    def getRRDPaths(self):
        return map(self.getRRDFileName, self.getRRDNames())

    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False

    def getRRDTemplates(self):
        default = self.getRRDTemplateByName(self.getRRDTemplateName())
        if not default:
            return []
        return [default]

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
        getUUID is defined on ManagedEntity.
        """
        return json.dumps({
            'type': 'METRIC_DATA',
            'contextUUID': self.getUUID(),
            'deviceUUID': self.device().getUUID(),
            'contextId': self.id
        }, sort_keys=True)

    def fullRRDPath(self):
        from PerformanceConf import performancePath
        return performancePath(self.rrdPath())

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
                        except pythonThresholdException, ex:
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

def updateCache(filenameValues):
    _cache.update(dict(filenameValues))
