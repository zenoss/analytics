##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import base64
import json

SEPARATOR_CHAR = "/"

from StringIO import StringIO
from cookielib import CookieJar
from twisted.internet import reactor
from twisted.web.client import Agent, CookieAgent, FileBodyProducer, HTTPConnectionPool
from twisted.web.http_headers import Headers
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.metrics import ensure_prefix
from Products.Zuul.facades.metricfacade import METRIC_URL_PATH, AGGREGATION_MAPPING, WILDCARD_URL_PATH
from Products.Zuul.interfaces import IAuthorizationTool
import logging

log = logging.getLogger('zen.metrics')

pool = None 

def getPool():
    global pool
    if pool is None:
        pool = HTTPConnectionPool(reactor)
        pool.maxPersistentPerHost=3
    return pool

class MetricServiceRequest(object):
    """
    A convience class for fetching metrics from CentralQuery that can
    be used by twisted daemons.
    """
    # use a shared cookie jar so all Metric requests can share the same session
    cookieJar = CookieJar()

    def __init__(self, userAgent):
        self._aggMapping = AGGREGATION_MAPPING
        urlstart = getGlobalConfiguration().get('metric-url', 'http://localhost:8080')
        self._metric_url = '%s/%s' % (urlstart, METRIC_URL_PATH)
        self._metric_url_v2 = '%s/%s' % (urlstart, WILDCARD_URL_PATH)
        creds = IAuthorizationTool(None).extractGlobalConfCredentials()
        auth = base64.b64encode('{login}:{password}'.format(**creds))
        self.agent = CookieAgent(Agent(reactor, pool=getPool(), connectTimeout=30), self.cookieJar)
        self._headers = Headers({
            'Authorization': ['basic %s' % auth],
            'content-type': ['application/json'],
            'User-Agent': ['Zenoss: %s' % userAgent]
        })
        self.onMetricsFetched = None

    def getMetrics(self, uuid, dpNames, cf='AVERAGE', rate=False, downsample="1h-avg", start=None, end=None,
                   deviceId=None, returnSet="EXACT"):
        metrics = []
        if isinstance(dpNames, basestring):
            dpNames = [dpNames]
        for dpName in dpNames:
            # TODO find callers
            name = ensure_prefix(deviceId, dpName)
            metrics.append(dict(
                metric=name,
                aggregator=self._aggMapping.get(cf.lower(), cf.lower()),
                rate=rate,
                format='%.2lf',
                tags=dict(contextUUID=[uuid]),
                name='%s_%s' % (uuid, dpName)
            ))

        request = dict(
            returnset=returnSet,
            start=start,
            end=end,
            downsample=downsample,
            metrics=metrics
        )
        body = FileBodyProducer(StringIO(json.dumps(request)))
        d = self.agent.request('POST', self._metric_url, self._headers, body)
        return d

    def fetchMetrics(self, metrics, start="1h-ago", end=None, returnSet="EXACT"):
        """
        Uses the CentralQuery V2 api to fetch metrics. Mainly that means wild cards can be used to fetch all metrics
        with the same name grouped by a tag. Usually used to retrieve a specific metric for all component on a device
        :param metrics: dictionary with required keys of metricName, tags and optional rpn defaults to empty,
        cf defatults to average, rate defaults to false, downsample defaults to 5m-avg
        :param start:
        :param end:
        :param returnSet:
        :return: deferred
        """
        metricQueries = []
        for metric in metrics:
            log.debug("fetchMetrics metrics %s", metric)
            cf = metric.get('cf', 'average')
            rate = metric.get('rate', False)
            tags = metric['tags']
            downsample = metric.get('downsample', '5m-avg')
            metricName = metric['metricName']
            metricQueries.append(dict(
                metric=metricName,
                downsample=downsample,
                aggregator=self._aggMapping.get(cf.lower(), cf.lower()),
                rate=rate,
                format='%.2lf',
                tags=tags
            ))

        request = dict(
            returnset=returnSet,
            start=start,
            end=end,
            queries=metricQueries
        )
        body = FileBodyProducer(StringIO(json.dumps(request)))
        log.debug("POST %s %s %s", self._metric_url_v2, self._headers, json.dumps(request))
        d = self.agent.request('POST', self._metric_url_v2, self._headers, body)
        return d
