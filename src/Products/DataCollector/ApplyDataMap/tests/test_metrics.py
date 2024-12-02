from unittest import TestCase
from mock import Mock, patch

import zope.component.event  # noqa, required for notify to function

from zope import component

from ..events import DatamapAppliedEvent
from ..metrics import (
    datamap_applied_time_logger,
    datamap_applied_time_tsdb_reporter,
    IMetricManager,
)


PATH = {"src": "Products.DataCollector.ApplyDataMap.metrics"}


class TestMetricReporting(TestCase):
    @patch("{src}.log".format(**PATH), autospec=True)
    def test_datamap_applied_time_logger(t, log):
        """notify(DatamapAppliedEvent) triggers rate_gauge"""

        t.assertIn(
            DatamapAppliedEvent,
            component.adaptedBy(datamap_applied_time_logger),
        )

        t0, t1 = 1, 3
        datamap = Mock(start_time=t0, end_time=t1)
        event = DatamapAppliedEvent(datamap)
        datamap_applied_time_logger(event)

        log.info.assert_called_with(
            "{'meta_type': '%s', 'start_time': %s, 'end_time': %s, 'dt': %s}",
            datamap.target.meta_type,
            t0,
            t1,
            t1 - t0,
        )

    @patch("{src}.getUtility".format(**PATH), autospec=True)
    def test_datamap_applied_time_tsdb_reporter(t, getUtility):
        metric_manager = Mock(name="metric_manager")
        getUtility.return_value = metric_manager
        t0, t1 = 1, 3
        datamap = Mock(start_time=t0, end_time=t1)
        event = DatamapAppliedEvent(datamap)

        datamap_applied_time_tsdb_reporter(event)

        getUtility.assert_called_with(
            IMetricManager, "zenhub_worker_metricmanager"
        )

        metric_manager.metric_writer.write_metric.assert_called_with(
            "datamap_applied_time",
            t1 - t0,
            t0,
            {"meta_type": datamap.target.meta_type},
        )
