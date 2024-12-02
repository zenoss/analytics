##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
import logging

SEPARATOR_CHAR = "/"
log = logging.getLogger("zen.metrics")

def ensure_prefix(metadata, metric):
    """
    Make sure that a metric name starts with a given prefix, joined by
    a separator. Returns the prefixed metric name.
    """

    if not metadata:
        return metric

    if isinstance(metadata, basestring):
        log.warn("ensure_prefix() called with string, please use metadata style calls.")
        prefix = metadata
    elif metadata.get('metricPrefix', False):
        prefix = metadata['metricPrefix']
    else:
        prefix = metadata['deviceId']

    if metric.startswith(prefix + SEPARATOR_CHAR):
        return metric
    return "%s%s%s" % (prefix, SEPARATOR_CHAR, metric)

def ensure_metadata_prefix(metadata, metric):
    """
    Make sure that a metric name starts with a given prefix, joined by
    a separator. Returns the prefixed metric name.

    New method to allow zenpacks to remain backward compatible and use metric metadata on newer installs
    Added 5.3.0

    :param metadata: dict, the metric metadata as returned from metricmixin
    :param metric: str, metric name to be prefixed
    :return: str, modified or unmodified metricname
    """
    return ensure_prefix(metadata, metric)
