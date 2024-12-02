##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging

import requests

from Products.ZenUtils.controlplane import configuration as cc_config
from Products.ZenUtils.MetricReporter import DEFAULT_METRIC_URL, getMetricData

log = logging.getLogger("zen.configcache.metrics")


class MetricReporter(object):

    def __init__(self, url=None, prefix="", tags=None):
        if not url:
            url = cc_config.consumer_url
            if not url:
                url = DEFAULT_METRIC_URL
        self._url = url
        self._prefix = prefix
        tags = dict(tags if tags is not None else {})
        tags.update(
            {
                "serviceId": cc_config.service_id,
                "instance": cc_config.instance_id,
                "hostId": cc_config.host_id,
                "tenantId": cc_config.tenant_id,
            }
        )
        self._tags = tags
        self._session = None
        self._instruments = {}

    def __contains__(self, name):
        """Return True if `name` matches a registered metric."""
        return name in self._instruments

    def add_tags(self, tags):
        self._tags.update(tags)

    def register(self, name, instrument):
        self._instruments[name] = instrument

    def save(self, name=None):
        metrics = list(
            self._get_metrics(
                self._instruments.keys() if name is None else (name,)
            )
        )
        if not metrics:
            return
        self._post_metrics(metrics)

    def _post_metrics(self, metrics):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Content-Type": "application/json",
                    "User-Agent": "Zenoss Service Metrics",
                }
            )
        post_data = {"metrics": metrics}
        log.debug("sending metric payload: %s", post_data)
        response = self._session.post(self._url, data=json.dumps(post_data))
        if response.status_code != 200:
            log.warning(
                "problem submitting metrics: %d, %s",
                response.status_code,
                response.text.replace("\n", "\\n"),
            )
            self._session = None
        else:
            log.debug("%d metrics posted", len(metrics))

    def _get_metrics(self, names):
        for name in names:
            instrument = self._instruments.get(name)
            data = getMetricData(instrument, name, self._tags, self._prefix)
            if data:
                for metric in data:
                    yield metric
