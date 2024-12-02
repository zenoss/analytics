##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from zope.component import adapter, getUtility

from Products.ZenHub.metricmanager import IMetricManager

from .events import DatamapAppliedEvent

log = logging.getLogger("zen.ApplyDataMap.metrics")


@adapter(DatamapAppliedEvent)
def datamap_applied_time_logger(datamap_applied_event):
    """Log datamap.apply time by target meta_type

    executed in response to DatamapAppliedEvent notifications
    """
    meta_type = datamap_applied_event.datamap.target.meta_type
    start = datamap_applied_event.datamap.start_time
    end = datamap_applied_event.datamap.end_time
    log.info(
        "{'meta_type': '%s', 'start_time': %s, 'end_time': %s, 'dt': %s}",
        meta_type,
        start,
        end,
        end - start,
    )


@adapter(DatamapAppliedEvent)
def datamap_applied_time_tsdb_reporter(datamap_applied_event):
    """Log datamap.apply time by target meta_type to TSDB"""
    metric_manager = getUtility(IMetricManager, "zenhub_worker_metricmanager")

    meta_type = datamap_applied_event.datamap.target.meta_type
    tags = {"meta_type": meta_type}
    start = datamap_applied_event.datamap.start_time
    end = datamap_applied_event.datamap.end_time
    dt = end - start

    metric_manager.metric_writer.write_metric(
        "datamap_applied_time", dt, start, tags
    )
    log.info(
        "datamap_applied_time_tsdb_reporter published",
    )
