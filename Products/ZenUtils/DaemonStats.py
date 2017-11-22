##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Globals
import time, os


class DaemonStats(object):
    """
    Utility for a daemon to write out internal performance statistics
    """

    def __init__(self):
        self.name = ""
        self.monitor = ""
        self.metric_writer = None
        self._threshold_notifier = None
        self._derivative_tracker = None
        self._service_id = None
        self._tenant_id = None
        self._instance_id = None

    def config(self, name, monitor, metric_writer, threshold_notifier,
               derivative_tracker):
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

        # when running inside control plane pull the service id from the environment
        if os.environ.get( 'CONTROLPLANE', "0") == "1":
            self._tenant_id = os.environ.get('CONTROLPLANE_TENANT_ID')
            self._service_id = os.environ.get('CONTROLPLANE_SERVICE_ID')
            self._instance_id = os.environ.get('CONTROLPLANE_INSTANCE_ID')

    def _context_id(self):
        return self.name + "-" + self.monitor

    def _contextKey(self):
        return "/".join(('Daemons', self.monitor))

    def _tags(self, metric_type):
        tags = {
            'daemon': self.name,
            'monitor': self.monitor,
            'metricType': metric_type,
            'internal': True
        }
        if self._service_id:
            tags['serviceId'] = self._service_id

        if self._tenant_id:
            tags['tenantId'] = self._tenant_id

        if self._instance_id:
            tags['instance'] = self._instance_id

        return tags

    def derive(self, name, value):
        """Write a DERIVE value and post any relevant events"""
        self.post_metrics(name, value, 'DERIVE')

    def counter(self, name, value):
        """Write a COUNTER value and post any relevant events"""
        self.post_metrics(name, value, 'COUNTER')

    def gauge(self, name, value):
        """Write a GAUGE value and post any relevant events"""
        self.post_metrics(name, value, 'GAUGE')

    def post_metrics(self, name, value, metric_type):
        tags = self._tags(metric_type)
        timestamp = time.time()

        context_id = self._context_id()
        if metric_type in {'DERIVE', 'COUNTER'}:
            # compute (and cache) a rate for COUNTER/DERIVE
            if metric_type == 'COUNTER':
                metric_min = 0
            else:
                metric_min = 'U'

            value = self._derivative_tracker.derivative(
                '%s:%s' % (context_id, name), (float(value), timestamp),
                min=metric_min)

        if value is not None:
            self._metric_writer.write_metric(name, value, timestamp, tags)
            # check for threshold breaches and send events when needed
            self._threshold_notifier.notify(
                self._contextKey(), context_id, self.name+'_'+name, timestamp, value)
