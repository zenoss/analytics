##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import itertools
import json
import logging
import os
import re
import requests
import sys

from collections import defaultdict
from datetime import datetime, timedelta
from zenoss.protocols.services import (
    ServiceConnectionError,
    ServiceResponseError,
)

from Products.ZenEvents import Event
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils import metrics
from Products.ZenUtils.metrics import ensure_prefix
from Products.Zuul.facades import ZuulFacade, ObjectNotFoundException
from Products.Zuul.interfaces import IAuthorizationTool, IInfo
from Products.Zuul.utils import safe_hasattr

DEFAULT_METRIC_URL = "http://localhost:8080/"
Z_AUTH_TOKEN = "ZAuthToken"

DATE_FORMAT = "%Y/%m/%d-%H:%M:%S"

METRIC_URL_PATH = "/api/performance/query"
WILDCARD_URL_PATH = "/api/performance/query2"
RENAME_URL_PATH = "/api/performance/rename"

AGGREGATION_MAPPING = {
    "average": "avg",
    "minimum": "min",
    "maximum": "max",
    "total": "sum",
    # TODO: get last agg function working
    "last": None,
}

_devname_pattern = re.compile("Devices/([^/]+)")

log = logging.getLogger("zen.MetricFacade")


def _isRunningFromUI(context):
    if not safe_hasattr(context, "REQUEST"):
        return False

    return safe_hasattr(context.REQUEST, "SESSION")


class MetricConnection(object):
    """Manages communication to Metric Server.
    """

    def __init__(
        self,
        auth_token,
        credentials,
        global_credentials,
        agent_suffix="python",
    ):
        """Initialize a MetricConnection object.

        :param auth_token: ZAuthToken used for authentication
        :param credentials: current user credentials
        :param global_credentials: global user credentials
        :param agent_suffix: suffix to be added to user agent
        """
        self._metric_url = getGlobalConfiguration().get(
            "metric-url", DEFAULT_METRIC_URL
        )
        self._auth_token = auth_token
        self._credentials = credentials
        self._global_credentials = global_credentials
        self._req_session = self._init_session(agent_suffix)

    def _init_session(self, agent_suffix):
        req_session = requests.Session()
        req_session.headers = {
            "content-type": "application/json",
            "User-Agent": "Zenoss MetricFacade: %s" % agent_suffix,
        }
        if self._auth_token:
            req_session.cookies[Z_AUTH_TOKEN] = self._auth_token
        return req_session

    def _uri(self, path):
        return "%s/%s" % (self._metric_url, path)

    def _server_request(self, path, request, auth, timeout):
        log.debug("METRICFACADE POST %s %s", path, request)
        try:
            response = self._req_session.post(
                self._uri(path),
                json.dumps(request),
                auth=auth,
                timeout=timeout,
            )
        except requests.exceptions.Timeout as e:
            raise ServiceConnectionError(
                "Timed out waiting for response from metric service: %s" % e, e
            )

        status_code = response.status_code
        if not (status_code >= 200 and status_code <= 299):
            log.debug("Server response error: %s %s", status_code, response)
            raise ServiceResponseError(
                response.reason,
                status_code,
                request,
                response,
                response.content,
            )

        return response.json()

    def _request(self, path, request, timeout):
        auth = None
        if not self._req_session.cookies.get(Z_AUTH_TOKEN):
            if self._credentials:
                auth = self._credentials
            else:
                auth = self._global_credentials

        try:
            return self._server_request(path, request, auth, timeout)
        except ServiceResponseError as e:
            if e.status == 401 and auth != self._global_credentials:
                # Try using global credentials.
                auth = self._global_credentials

                if Z_AUTH_TOKEN in self._req_session.cookies:
                    del self._req_session.cookies[Z_AUTH_TOKEN]

                log.debug(
                    "Authorization failed. Trying to use global credentials"
                )
                return self._server_request(path, request, auth, timeout)
            else:
                raise

    def request(self, path, request, timeout=10):
        """
        Performs request to Metrics Server.

        For authentication, credentials will be retrieved from the following
        attributes according to the shown order:
           1. `auth_token`
           2. `credentials`
           3. `global_credentials`
        The next lower priority attribute is used only if the previous
        attribute is None.

        In case of authentication error, tries to use global credentials for
        authentication.

        :param path: path to API method on Metric Server without scheme, host
                     and port. (i.e. /api/performance/query)
        :param request: dict with request parameters
        :param timeout: timeout in seconds to wait for response from server
        :return: decoded response from server or None if error occurred
        """
        try:
            return self._request(path, request, timeout)
        except ServiceResponseError as e:
            # there was an error returned by the metric service, log it here
            log.error(
                "Error fetching request: %s \n"
                "Response from the server (return code %s): %s",
                request,
                e.status,
                e.content,
            )
        except ServiceConnectionError as e:
            log.error("Error connecting with request: %s \n%s", request, e)

    def stream_request(self, path, request, timeout=10):
        auth = None
        if not self._req_session.cookies.get(Z_AUTH_TOKEN):
            if self._credentials:
                auth = self._credentials
            else:
                auth = self._global_credentials

        try:
            log.info("posting request")
            resp = self._req_session.post(
                self._uri(path),
                json.dumps(request),
                auth=auth,
                timeout=timeout,
                stream=True,
            )
            log.info("finished posting request")

            if not (resp.status_code >= 200 and resp.status_code <= 299):
                raise ServiceResponseError(
                    resp.reason, resp.status_code, request, resp, resp.content
                )

            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        yield line.decode("ascii")

        except requests.exceptions.Timeout as e:
            log.error("Error connecting with request: %s \n%s", request, e)

        except ServiceResponseError as e:
            if e.status == 401 and auth != self._global_credentials:
                # Try using global credentials.
                auth = self._global_credentials

                if Z_AUTH_TOKEN in self._req_session.cookies:
                    del self._req_session.cookies[Z_AUTH_TOKEN]

                log.debug(
                    "Authorization failed. Trying to use global credentials"
                )
                resp = self.stream_request(path, request, auth, timeout)

                if not (resp.status_code >= 200 and resp.status_code <= 299):
                    log.error(
                        "Centralquery responded with an error code %s while "
                        "processing request %s: %s",
                        resp.status_code,
                        request,
                        resp.reason,
                    )

                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if line:
                            yield line.decode("ascii")
            else:
                log.error(
                    "Error fetching request: %s \n"
                    "Response from the server (return code %s): %s",
                    request,
                    e.status,
                    e.content,
                )


class MetricFacade(ZuulFacade):
    def __init__(self, context):
        super(MetricFacade, self).__init__(context)

        authorization = IAuthorizationTool(self.context)

        auth_token = None
        credentials = None

        global_credentials_dict = authorization.extractGlobalConfCredentials()
        global_credentials = (
            global_credentials_dict["login"],
            global_credentials_dict["password"],
        )

        if _isRunningFromUI(context):
            auth_token = context.REQUEST.cookies.get(Z_AUTH_TOKEN, None)
            if not auth_token:
                credentials_dict = authorization.extractCredentials(
                    context.REQUEST
                )
                credentials = (
                    credentials_dict["login"],
                    credentials_dict["password"],
                )
        else:
            credentials = None

        agent_suffix = "python"
        if sys.argv[0]:
            agent_suffix = os.path.basename(sys.argv[0].rstrip(".py"))

        self._metrics_connection = MetricConnection(
            auth_token, credentials, global_credentials, agent_suffix
        )

    def getLastValue(self, context, metric):
        """Retrieves the last value for a metric on a context.

        Returns -1 if not found.
        """
        result = self.getValues(context, [metric])
        if result and metric in result:
            return result[metric]
        return -1

    def getMultiValues(
        self,
        contexts,
        metrics,
        start=None,
        end=None,
        returnSet="LAST",
        downsample=None,
    ):
        """Consider using `getMetricsForContexts` instead.

        Use this method when you need one or more metrics on multiple contexts.

        Returns all the values for the given contexts and the given metrics
        over the date range specified by start to end.

        @param contexts: array of either uids or model objects
        @param metrics: name of metrics (datapoints).
        @param start: defaults to now - dmd.defaultDateRange can be either a
            timestamp or a string in DATE_FORMAT format.
        @param end: defaults to now, can be either a timestamp or a string in
            DATE_FORMAT format.
        @param returnSet: default "LAST" (which returns the last value) the
            other options are ALL which returns everthing, and EXACT which
            returns what is in the date range.
        @param downsample: can be either the string of the form 1m-avg or a
            number which will be assumed to be seconds averaged.
        If the returnSet is EXACT or ALL, then you are returned metrics in
        this form:
        {
            # context UUID
            '55d1bbf8-efab-4175-b585-1d748b275b2a': {
                # metric id, is a list of timestamp and values
                'sysUpTime': [
                    {timestamp=1234567, value=1},
                    {timestamp=1234568, value=2}
                ],
                'laLoadInt5': [
                    {timestamp=1234567, value=100},
                    {timestamp=1234568, value=200}
                ]
            }

        }
        If the returnSet is LAST then you get the results of the form
        {
            '55d1bbf8-efab-4175-b585-1d748b275b2a': {
                'sysUpTime': 2,
                'laLoadInt5': 4
            }

        }
        """
        results = {}
        data = self.queryServer(
            contexts,
            metrics,
            start=start,
            end=end,
            returnSet=returnSet,
            downsample=downsample,
        )
        if returnSet == "LAST":
            return data
        # if the returnSet is exact or all then organize the results into
        # something more digestable
        for row in data:
            key, metric = row["metric"].split("|", 1)
            if not results.get(key):
                results[key] = defaultdict(list)
            for dp in row.get("datapoints", []):
                if not dp["value"] is None and dp["value"] != u"NaN":
                    results[key][metric].append(
                        dict(timestamp=dp["timestamp"], value=dp["value"])
                    )
        return results

    def getValues(
        self,
        context,
        metrics,
        start=None,
        end=None,
        format="%.2lf",
        extraRpn="",
        cf="avg",
        returnSet="LAST",
        downsample=None,
    ):
        """
        Return a dict of key value pairs where metric names are the keys and
        the most recent value in the given time range is the value.

        Note: all dates must be passed in in the format:
        strftime("%Y/%m/%d-%H:%M:%S-%z") or as an unix timestamp.

        Use this method when you need to get one or more metrics for a single
        context.

        @param context: One or more model object for which we are fetching
            metrics for.
        @param dataPointIds: array of the ids of datapoints.
            An example would be: ['sysUpTime'].
        @param start: start of the date range we are examining metrics for,
            defaults to now - context.defaultDateRange
            (defined in DataRoot.py). Does accept unix timestamps.
        @param end: end time of the date range, defaults to now. Does accept
            unix timestamps.
        @param format: the format we are returning the data in
        @param extraRpn: an extra rpn expression appended to the datapoint
            RPN expression.
        @param cf: Consolidation functions, valid consolidation functions are
            avg, min, max, and sum.
        @param returnSet: default "LAST" (which returns the last value) the
            other options are ALL which returns everthing, and EXACT which
            returns what is in the date range.
        @param downsample: can be either the string of the form 1m-avg or a
            number which will be assumed to be seconds averaged.
        @return: Dictionary of [dataPointId: value]
        """
        results = self.queryServer(
            context,
            metrics,
            start=start,
            end=end,
            format=format,
            extraRpn=extraRpn,
            cf=cf,
            returnSet=returnSet,
            downsample=downsample,
        )
        if len(results.values()):
            return results.values()[0]
        return {}

    def _defaultStartAndEndTime(self, start, end, returnSet):
        # check to see if the user entered a unix timestamp
        if isinstance(start, (int, long, float)):
            start = self._formatTime(datetime.fromtimestamp(start))

        if isinstance(end, (int, long, float)):
            end = self._formatTime(datetime.fromtimestamp(end))

        # if no start time or end time specified use the
        # defaultDateRange (which is acquired from the dmd)
        if end is None:
            end = self._formatTime(datetime.today())
        if start is None and returnSet != "LAST":
            start = self._formatTime(
                datetime.today()
                - timedelta(seconds=self._dmd.defaultDateRange)
            )
        elif start is None and returnSet == "LAST":
            start = self._formatTime(
                datetime.today() - timedelta(seconds=3600)
            )
        return start, end

    def queryServer(
        self,
        contexts,
        metrics,
        start=None,
        end=None,
        format="%.2lf",
        extraRpn="",
        cf="avg",
        returnSet="LAST",
        downsample=None,
    ):
        subjects = []
        # make sure we are always dealing with a list
        if not isinstance(contexts, (list, tuple)):
            contexts = [contexts]

        for context in contexts:
            if isinstance(context, basestring):
                subjects.append(self._getObject(context))
            else:
                subjects.append(context)

        # build the metrics section of the query
        datapoints = []
        metricnames = {}
        for ds in metrics:
            # Find the first occurrence of a datapoint on a context.
            # In theory it is possible that a passed in metric exists on one
            # context but not another.
            for subject in subjects:
                dp = next(
                    (
                        d
                        for d in subject._getRRDDataPointsGen()
                        if ds in d.name()
                    ),
                    None,
                )
                if dp is None:
                    continue
                else:
                    # We have found a definition for a datapoint,
                    # use it and continue on.
                    metricnames[dp.name()] = ds
                    for subject in subjects:
                        datapoints.extend(
                            self._buildMetric(
                                subject, dp, cf, extraRpn, format
                            )
                        )
                    break
        # no valid datapoint names were entered
        if not datapoints:
            return {}

        start, end = self._defaultStartAndEndTime(start, end, returnSet)
        request = self._buildRequest(
            subjects, datapoints, start, end, returnSet, downsample
        )
        # submit it to the client
        content = self._metrics_connection.request(METRIC_URL_PATH, request)
        if content is None:
            return {}

        if (
            content
            and content.get("results") is not None
            and returnSet == "LAST"
        ):
            # Output of this request should be something like this:
            # [{u'timestamp': 1376477481, u'metric': u'sysUpTime',
            #   u'value': 2418182400.0, u'tags': {u'device':
            #   u'55d1bbf8-efab-4175-b585-1d748b275b2a', u'uuid':
            #   u'55d1bbf8-efab-4175-b585-1d748b275b2a', u'datasource':
            #   u'sysUpTime'}}]
            #
            results = defaultdict(dict)
            for item in content["results"]:
                key, metric = item["metric"].split("|", 1)
                if item.get("datapoints"):
                    results[key][metricnames[metric]] = float(
                        format % item["datapoints"][0]["value"]
                    )
            return results
        else:
            if returnSet == "ALL":
                return content
            return content.get("results")

    def _formatDownsample(self, downsample):
        if isinstance(downsample, int):
            downsample = "%ss-avg" % downsample
        return downsample

    def _buildRequest(
        self, contexts, metrics, start, end, returnSet, downsample
    ):
        request = {
            "returnset": returnSet,
            "start": start,
            "end": end,
            "metrics": metrics,
        }
        if downsample is not None:
            request["downsample"] = self._formatDownsample(downsample)
        return request

    def _buildTagsFromContextAndMetric(self, context, dsId):
        return dict(key=[context.getResourceKey()])

    def _get_key_from_tags(self, tags):
        key = tags.get("key", "")
        if isinstance(key, (list, set, tuple)):
            key = key[0]
        return key

    def _buildMetric(self, context, dp, cf, extraRpn="", format=""):
        datasource = dp.datasource()
        dsId = datasource.id
        info = IInfo(dp)

        # find out our aggregation function
        agg = AGGREGATION_MAPPING.get(cf.lower(), cf.lower())
        rateOptions = info.getRateOptions()
        tags = self._buildTagsFromContextAndMetric(context, dsId)
        metricname = dp.name()
        key = self._get_key_from_tags(tags)
        search = _devname_pattern.match(key)
        if search:
            metricname = metrics.ensure_prefix(
                context.getMetricMetadata(), metricname
            )
        name = context.getResourceKey() + "|" + dp.name()
        metric = dict(
            metric=metricname,
            aggregator=agg,
            tags=tags,
            rate=info.rate,
            name=name,
        )
        combined_metric = [metric]
        if rateOptions:
            metric["rateOptions"] = rateOptions
        if extraRpn:
            metric["emit"] = "false"
            metric["name"] = "{}-raw".format(dp.name())
            new_metric = dict(
                expression="rpn:{}-raw,{}".format(dp.name(), extraRpn),
                format=format,
                name=name,
            )
            combined_metric.append(new_metric)
        else:
            metric["format"] = format
        return combined_metric

    def _formatTime(self, t):
        """
        Formats a datetime object
        @return: the date as a string.
        """
        return t.strftime(DATE_FORMAT)

    def _buildWildCardMetrics(
        self, device, metricName, cf="avg", isRate=False, format="%.2lf"
    ):
        # find out our aggregation function
        agg = AGGREGATION_MAPPING.get(cf.lower(), cf.lower())
        metric = dict(
            metric=ensure_prefix(device.id, metricName),
            aggregator=agg,
            format=format,
            tags={"contextUUID": ["*"]},
            rate=isRate,
        )
        return metric

    @deprecated
    def getMetricsByDevice(
        self,
        device,
        metrics,
        start=None,
        end=None,
        format="%.2lf",
        cf="avg",
        returnSet="LAST",
        downsample=None,
        timeout=10,
        isRate=False,
    ):
        """
        @deprecated see getMetricsForContexts

        Gets a set of metrics for every component under a device.

        Warning: only works with component metrics that do not include context
        information in the metricname.
        """
        start, end = self._defaultStartAndEndTime(start, end, returnSet)
        if isinstance(metrics, basestring):
            metrics = [metrics]
        metricRequests = [
            self._buildWildCardMetrics(device, metric, cf, isRate, format)
            for metric in metrics
        ]
        request = self._buildRequest(
            [device], metricRequests, start, end, returnSet, downsample
        )
        request["queries"] = request["metrics"]
        del request["metrics"]
        content = self._metrics_connection.request(
            WILDCARD_URL_PATH, request, timeout=timeout
        )
        if content is None:
            return []

        # check for bad status and log what happened
        for status in content["statuses"]:
            if (
                status["status"] == u"ERROR"
                and "not such name" not in status["message"]
            ):
                log.error(status["message"])
        return content["series"]

    def _getDataPoint(self, devices, metric):
        for subject in devices:
            dp = next(
                (
                    d
                    for d in subject._getRRDDataPointsGen()
                    if metric in d.name()
                ),
                None,
            )
            if dp is not None:
                return dp

        return None

    def getAggregatedMetric(
        self,
        device,
        componentType,
        metricName,
        returnSet=None,
        start="1h-ago",
        end="30s-ago",
        agg="sum",
        downSample=None,
        format="",
    ):
        """
        For a device returns the aggregate time series for a metric belonging
        to components. e.g. aggregate interface usage for all interfaces.

        :param device: Device object
        :type device: Device
        :param componentType: the name of the component meta type, used to
            look up metric definition (eg. rate, rpn etc).
        :type componentType: str
        :param metricName: name of the metric
        :type metricName: str
        :param start: start of time range, defaults to 1 hour ago
        :type start: str or int,float,long. string can be of the form "1h-ago"
        :param end: end of time range, defaults to 30s ago. Aggregate metrics
            benefit from a bit of lag.
        :type end: str or int,float,long. string can be of the form "1h-ago"
        :param agg: aggregation function for the time series. e.g. avg, sum
        :type agg: str
        :param downSample: how to downsample series. e.g. 1m-avg
        :type downSample: str
        :return: series for the metric
        """
        components = device.getDeviceComponents(type=componentType)
        if not components:
            raise ObjectNotFoundException(
                "No components of type %s found" % componentType
            )
        # get the first one to determine datapoint information
        component = components[0]
        dataPoint = component.getRRDDataPoint(metricName)
        if not dataPoint:
            raise ObjectNotFoundException(
                "Metric %s for %s not found" % (metricName, componentType)
            )

        metric = self._buildMetric(component, dataPoint, agg, format=format)
        # Replace context specific tag with just device tag
        for m in metric:
            # Remove contextid tag so we can query for component metrics
            # across device.
            m["tags"] = {"device": [device.id]}

        start, end = self._defaultStartAndEndTime(start, end, returnSet)
        request = self._buildRequest(
            None, metric, start, end, returnSet, downSample
        )
        # submit it to the client
        content = self._metrics_connection.request(METRIC_URL_PATH, request)
        if content is None:
            return {}
        if format and content.get("results") is not None:
            for item in content["results"]:
                if item.get("datapoints", False):
                    for dp in item.get("datapoints"):
                        dp["value"] = float(format % dp["value"])
        return content

    def getMetricsForContexts(
        self,
        contexts,
        metricNames,
        start=None,
        end=None,
        format="%.2lf",
        cf="avg",
        downsample=None,
        timeout=10,
        isRate=False,
    ):
        """Returns the metrics for all the contexts given.

        :param contexts: the device or component with metrics, only needs to
            have the getMetricMetadata method.
        :param metricNames: names of the metrics to be fetched for each context
        :param start: timestamp
        :param end: timestamp
        :param format:
        :param cf:
        :param downsample: eg. 5m-avg, no downsample by default
        :param timeout: timeout for request
        :param isRate: if the metric should be returned as a rate,
            False by default.
        :returns map with keys of resource key (FQN of context) to map that
            contains metric name keys to list of datapoints, datapoints is a
            map with 'timestamp' and 'value' keys.
        """
        # Series is the fully qualified metric name (with device[component]
        # prefix). This map tracks all the different contexts
        # (device/component) with the same series name.
        seriesToCtxKey = defaultdict(list)

        # each series name maps back to the original metricName requested
        seriesToMetricNames = {}
        for ctx in contexts:
            mData = ctx.getMetricMetadata()
            for mName in metricNames:
                seriesName = metrics.ensure_prefix(mData, mName)
                seriesToCtxKey[seriesName].append(mData["contextKey"])
                seriesToMetricNames[seriesName] = mName

        agg = AGGREGATION_MAPPING.get(cf.lower(), cf.lower())
        metricRequests = []

        if downsample is not None:
            downsample = self._formatDownsample(downsample)

        for seriesName, ctxKeys in seriesToCtxKey.items():
            contextKeys = ctxKeys
            # if we have a bunch just do a wildcard.
            if len(ctxKeys) > 200:
                contextKeys = ["*"]

            metricReq = dict(
                metric=seriesName,
                aggregator=agg,
                format=format,
                tags={"key": contextKeys},
                rate=isRate,
                downsample=downsample,
            )
            metricRequests.append(metricReq)

        # Only EXACT resultsets are supported yet.
        returnSet = "EXACT"
        start, end = self._defaultStartAndEndTime(start, end, returnSet)
        request = self._buildRequest(
            [], metricRequests, start, end, returnSet, downsample=None
        )
        request["queries"] = request["metrics"]
        del request["metrics"]

        content = self._metrics_connection.request(
            WILDCARD_URL_PATH, request, timeout=timeout
        )
        if content is None:
            return {}

        # check for bad status and log what happened
        for status in content["statuses"]:
            if (
                status["status"] == u"ERROR"
                and u"No such name" not in status["message"]
            ):
                log.error(status["message"])

        results = {}
        for row in content["series"]:
            mName = seriesToMetricNames[row["metric"]]
            key = row["tags"]["key"]
            if key not in results:
                results[key] = defaultdict(list)
            for ts, value in row.get("datapoints", []):
                if value is not None and value != u"NaN":
                    results[key][mName].append(dict(timestamp=ts, value=value))

        return results

    # Should not be used as it won't always work and is very inefficent.
    @deprecated
    def getMetricsForDevices(
        self,
        devices,
        metrics,
        start=None,
        end=None,
        format="%.2lf",
        cf="avg",
        downsample=None,
        timeout=10,
        isRate=False,
    ):
        """
        @deprecated see getMetricsForContexts
        Gets a set of metrics for every component under a each device.
        """
        # Only EXACT resultsets are supported yet.
        returnSet = "EXACT"

        start, end = self._defaultStartAndEndTime(start, end, returnSet)
        if isinstance(metrics, basestring):
            metrics = [metrics]

        metricnames = {}
        metricRequests = []
        for device in devices:
            for metric in metrics:
                dp = self._getDataPoint(
                    itertools.chain((device,), device.getDeviceComponents()),
                    metric,
                )
                if dp is not None:
                    metricnames[dp.name()] = metric
                    metricRequests.append(
                        self._buildWildCardMetrics(
                            device, dp.name(), cf, isRate, format
                        )
                    )

        request = self._buildRequest(
            devices, metricRequests, start, end, returnSet, downsample
        )
        request["queries"] = request["metrics"]
        del request["metrics"]
        content = self._metrics_connection.request(
            WILDCARD_URL_PATH, request, timeout=timeout
        )
        if content is None:
            return {}

        # check for bad status and log what happened
        for status in content["statuses"]:
            if (
                status["status"] == u"ERROR"
                and u"No such name" not in status["message"]
            ):
                log.error(status["message"])

        results = {}
        for row in content["series"]:
            _, metric = row["metric"].split("/", 1)
            key = row["tags"]["key"]
            if key not in results:
                results[key] = defaultdict(list)
            for ts, value in row.get("datapoints", []):
                if value is not None and value != u"NaN":
                    results[key][metricnames[metric]].append(
                        dict(timestamp=ts, value=value)
                    )

        return results

    # This method is supposed to run as a facade method job.
    def renameDevice(self, oldId, newId):
        path = RENAME_URL_PATH
        timeout = 120
        totalFails = 0
        success = False
        request = {}

        def processRename():
            resp = self._metrics_connection.stream_request(
                path, request, timeout=timeout
            )

            # Initially, central query was supposed to send a message every
            # once in a while. However, due to a buffer somewhere between
            # central query and zenoss, streaming was not smooth but chunked.
            # As a workaround, central query sends a message per every metric
            # renaming and some messages are skipped here.
            logFreq = 5000

            nFails = 0

            # Log the fist line, the last line, and every logFreq lines
            jsonLine = None
            i = 0
            for line in resp:
                jsonLine = json.loads(line)
                logtype = jsonLine["type"]
                if logtype == "info":
                    log.info(jsonLine["content"])
                elif logtype == "progress":
                    if i % logFreq == 0:
                        log.info(jsonLine["content"])
                elif logtype == "error":
                    log.error(jsonLine["content"])
                    nFails += 1
                else:
                    log.error(
                        "Unknown log msg type received from central query: "
                        "type %s, content %s",
                        logtype,
                        jsonLine["content"],
                    )

                i += 1

            # Log the last progress msg because the progress msgs are printed
            # at every once in a while so that the last line can be omitted.
            if jsonLine and jsonLine["type"] == "progress":
                log.info(jsonLine["content"])

            return nFails

        try:
            # metrics
            request = {
                "oldName": oldId + "/",
                "newName": newId + "/",
                "type": "metric",
                "patternType": "prefix",
            }
            totalFails += processRename()

            # key tagv for components metrics
            request = {
                "oldName": "Devices/" + oldId + "/",
                "newName": "Devices/" + newId + "/",
                "type": "tagv",
                "patternType": "prefix",
            }
            totalFails += processRename()

            # key tagv for device metrics
            request = {
                "oldName": "Devices/" + oldId,
                "newName": "Devices/" + newId,
                "type": "tagv",
                "patternType": "whole",
            }
            totalFails += processRename()

            # device tagv
            request = {
                "oldName": oldId,
                "newName": newId,
                "type": "tagv",
                "patternType": "whole",
            }
            totalFails += processRename()

            success = totalFails == 0

            # Trigger an event that indicates the completion of a renaming
            # request in central query.
            if success:
                message = (
                    "Reassociating performance data for device {} with new "
                    "ID {} has been completed successfully. See the job log "
                    "for the details.".format(oldId, newId)
                )
                summary = (
                    "Reassociating performance data for device {} with new "
                    "ID {} completed.".format(oldId, newId)
                )
                eventClass = "/Status/Update"
                severity = Event.Info
            else:
                message = (
                    "Reassociating performance data for device {} with new "
                    "ID {} has been completed. However, reassociation of "
                    "some metrics were unsuccessful. See the job log for "
                    "the details.".format(oldId, newId)
                )
                summary = (
                    "Reassociating performance data for device {} with new "
                    "ID {} completed, but some metrics are not "
                    "reassociated.".format(oldId, newId)
                )
                eventClass = "/App/Job/Fail"
                severity = Event.Error

            self._dmd.ZenEventManager.sendEvent(
                dict(
                    device=newId,
                    eventClass=eventClass,
                    severity=severity,
                    summary=summary,
                    message=message,
                )
            )
        except Exception as e:
            log.exception(
                "Exception thrown while re-identifying device %s to %s: %s",
                oldId,
                newId,
                e,
            )
        finally:
            if success:
                # Update renameInProgress so that the collection resumes.
                dev = self._dmd.Devices.findDeviceByIdExact(newId)
                if dev:
                    dev.renameInProgress = False
                    from transaction import commit
                    commit()
                else:
                    log.error(
                        "Cannot find a device after reidentifying  "
                        "old-id=%s new-id=%s",
                        oldId,
                        newId,
                    )
                    success = False

            return {"success": success, "message": None}
