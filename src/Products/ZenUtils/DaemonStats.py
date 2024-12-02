##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time

from .controlplane import configuration as cc_config


class DaemonStats(object):
    """
    Utility for a daemon to write out internal performance statistics.
    """

    def __init__(self):
        self.name = ""
        self.monitor = ""
        self.metric_writer = None
        self._threshold_notifier = None
        self._derivative_tracker = None
        self._ctx_id = None
        self._ctx_key = None

        tags = {"internal": True}
        # Only capture the control center variables that have a value.
        if cc_config.service_id:
            tags["serviceId"] = cc_config.service_id
        if cc_config.tenant_id:
            tags["tenantId"] = cc_config.tenant_id
        if cc_config.instance_id:
            tags["instance"] = cc_config.instance_id
        self._common_tags = tags

    def config(
        self,
        name,
        monitor,
        metric_writer,
        threshold_notifier,
        derivative_tracker,
    ):
        """
        Initialize the object.  We could do this in __init__, but
        that would delay creation to after configuration time, which
        may run asynchronously with collection or heartbeats.  By
        deferring initialization, this object implements the Null
        Object pattern until the application is ready to start writing
        real statistics.
        """
        self.name = name
        self.monitor = monitor
        self._metric_writer = metric_writer
        self._threshold_notifier = threshold_notifier
        self._derivative_tracker = derivative_tracker

        # Update the common tags
        self._common_tags.update({"daemon": name, "monitor": monitor})

        # evaluate identifiers once
        self._ctx_id = name + "-" + monitor
        self._ctx_key = "/".join(("Daemons", monitor))

    def _tags(self, metric_type):
        tags = self._common_tags.copy()
        tags["metricType"] = metric_type
        return tags

    def derive(self, name, value):
        """Write a DERIVE value and post any relevant events"""
        self.post_metrics(name, value, "DERIVE")

    def counter(self, name, value):
        """Write a COUNTER value and post any relevant events"""
        self.post_metrics(name, value, "COUNTER")

    def gauge(self, name, value):
        """Write a GAUGE value and post any relevant events"""
        self.post_metrics(name, value, "GAUGE")

    def post_metrics(self, name, value, metric_type):
        tags = self._tags(metric_type)
        timestamp = time.time()

        if metric_type in {"DERIVE", "COUNTER"}:
            # compute (and cache) a rate for COUNTER/DERIVE
            if metric_type == "COUNTER":
                metric_min = 0
            else:
                metric_min = "U"

            value = self._derivative_tracker.derivative(
                "%s:%s" % (self._ctx_id, name),
                (float(value), timestamp),
                min=metric_min,
            )

        if value is not None:
            self._metric_writer.write_metric(name, value, timestamp, tags)
            # check for threshold breaches and send events when needed
            self._threshold_notifier.notify(
                self._ctx_key,
                self._ctx_id,
                self.name + "_" + name,
                timestamp,
                value,
            )
