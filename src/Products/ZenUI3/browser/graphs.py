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

from collections import OrderedDict

from Products.Five.browser import BrowserView

from Products.ZenUtils.Time import LocalDateTimeFromMilli

log = logging.getLogger("zen.graphexport")


class ExportGraph(BrowserView):
    """
    This view takes the chart data and sends it back to the client as a CSV.
    """

    def __call__(self, *args, **kwargs):
        """
        Takes the posted "plots" element and exports a CSV
        """
        title = self.request.form.get("title", "graph_export")
        start = self.request.form.get("start", "Unknown")
        end = self.request.form.get("end", "Unknown")
        uid = self.request.form.get("uid", None)
        plots = self.request.form.get("plots")
        units = "Units: {0}".format(self.request.form.get("units"))
        # come up with the title
        if uid:
            obj = self.context.unrestrictedTraverse(uid)
            exportTitle = "{title}_{name}_from_{start}_to_{end}".format(
                title=title.replace(" ", "_"),
                start=start,
                end=end,
                name=obj.titleOrId(),
            )
        else:
            exportTitle = title.replace(" ", "_")

        if not plots:
            self.request.response.write("Unable to load chart data.")
            return
        try:
            plots = json.loads(plots)
        except Exception as e:
            log.exception(e)
            self.request.response.write(
                "POST data contains invalid json %s" % plots
            )
        self.request.response.setHeader(
            "Content-Type", "application/vnd.ms-excel"
        )
        self.request.response.setHeader(
            "Content-Disposition", "attachment; filename=%s.csv" % exportTitle
        )

        # write the device information

        # construct the labels, Time will always be first
        labels = ["Time"] + [p["key"] for p in plots] + [units]

        # timestamps is a dictionary of values indexed by the time. This is to
        # make sure we have a row for every unique timestamp in our csv, even
        # if # it is not present for all metrics
        timestamps = {}
        for p in plots:
            for value in p["values"]:
                # x is always the timestamp and y is always the
                # value at that time.
                time = value["x"]
                if not timestamps.get(time):
                    timestamps[time] = dict()
                timestamps[time][p["key"]] = value["y"]
        ordered_timestamps = OrderedDict(
            sorted(timestamps.items(), reverse=True)
        )

        # writeExportRows works best with a dictionary of
        # data will looks something like this
        #   [
        #     {
        #       u'15 Minute': 0.72,
        #       u'5 Minute': 0.8,
        #       u'1 Minute': 0.88,
        #       'Time': '2013/10/04 13:43:20.000'
        #     },
        #     ...
        #   ]
        data = []
        for time, values in ordered_timestamps.iteritems():
            datum = dict(Time=LocalDateTimeFromMilli(time))
            datum.update(values)
            data.append(datum)
        self.context.dmd.writeExportRows(labels, data, self.request.response)
