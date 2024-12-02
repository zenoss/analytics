#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import argparse
import logging
import subprocess
import time

from gather import MetricGatherer, ServiceMetrics


log = logging.getLogger("zenoss.servicemetrics")
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log.setLevel(logging.INFO)


class StorageMetrics(ServiceMetrics):
    def __init__(self, options):
        super(StorageMetrics, self).__init__(options)
        self.name = options.name

    def build_gatherer(self):
        return StorageMetricGatherer(self.name)


class StorageMetricGatherer(MetricGatherer):
    METRICS_QUERY = "/opt/zenoss/bin/metrics/mysqlmetrics.sh"

    def __init__(self, name):
        MetricGatherer.__init__(self)
        self.name = name

    def get_metrics(self):
        metrics = []
        ts = time.time()
        tags = {"zenoss_storage": self.name}
        try:
            response = subprocess.check_output([self.METRICS_QUERY, self.name])
        except Exception as e:
            log.error("Error gathering mysql storage info: %s" % e)
            return []
        total_size = 0
        for line in response.split("\n"):
            if not line:
                continue
            parsed = line.split("\t")
            table, size, free = parsed[0], parsed[1], parsed[2]
            table_size = "zenoss.mariadb.%s.%s.size" % (self.name, table)
            table_free = "zenoss.mariadb.%s.%s.free" % (self.name, table)
            total_size += int(size)
            metrics.append(self.build_metric(table_size, size, ts, tags))
            metrics.append(self.build_metric(table_free, free, ts, tags))
        metrics.append(
            self.build_metric(
                "zenoss.mariadb.%s.total.size" % self.name,
                total_size,
                ts,
                tags,
            )
        )
        return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--interval",
        dest="interval",
        type=float,
        default=30,
        help="polling interval in seconds",
    )
    parser.add_argument(
        "name", type=str, default=30, help="name of service monitored"
    )
    args = parser.parse_args()

    rm = StorageMetrics(options=args)
    rm.run()
