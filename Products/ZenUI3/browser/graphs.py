##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import json
import logging
from datetime import datetime
from Products.ZenUtils.Time import LocalDateTimeFromMilli
from Products.Five.browser import BrowserView
log = logging.getLogger('zen.graphexport')


class ExportGraph(BrowserView):
    """
    """
    def __call__(self, *args, **kwargs):
        """
        Takes the posted "plots" element and exports a CSV
        """
        title = self.request.form.get('title', 'graph_export')
        plots = self.request.form.get('plots')
        if not plots:
            self.request.response.write("Unable to load chart data.")
            return
        try:
            plots = json.loads(plots)
        except Exception, e:
            log.exception(e)
            self.request.response.write("POST data contains invalid json %s" % plots)
        self.request.response.setHeader(
            'Content-Type', 'application/vnd.ms-excel')
        self.request.response.setHeader(
            'Content-Disposition', 'attachment; filename=%s.csv'  % title.replace(' ', '_'))

        # construct the labels, Time will always be first
        labels = ['Time'] + [p['key'] for p in plots]

        # timestamps is a dictionary of values indexed by the time. This is to
        # make sure we have a row for every unique timestamp in our csv, even if
        # it is not present for all metrics
        timestamps = {}
        for p in plots:
            for value in p['values']:
                # x is always the timestamp and y is always the value at that time
                time = value['x']
                if not timestamps.get(time):
                    timestamps[time] = dict()
                timestamps[time][p['key']] = value['y']

        # writeExportRows works best with a dictionary of
        # data will looks something like this [{u'15 Minute': 0.72, u'5 Minute': 0.8, u'1 Minute': 0.88, 'Time': '2013/10/04 13:43:20.000'}, ...]
        data = []
        for time, values in timestamps.iteritems():
            datum = dict(Time=LocalDateTimeFromMilli(time))
            datum.update(values)
            data.append(datum)
        self.context.dmd.writeExportRows(labels, data, self.request.response)
