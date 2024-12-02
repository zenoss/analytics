##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """export

Given a list of events to export, format them
appropriately and then return back a string
"""

import json
import logging

from datetime import datetime

import pytz

from Products.Five.browser import BrowserView

from Products.ZenUtils.jsonutils import unjson
from Products.ZenUtils.Time import convertJsTimeFormatToPy
from Products.Zuul.routers.zep import EventsRouter

from .interfaces import IEventManagerProxy

log = logging.getLogger("zen.eventexport")

DETAILS_KEY = "details"


class EventsExporter(BrowserView):
    def __call__(self):
        body = self.request.form["body"]
        state = unjson(body)
        params = state["params"]
        options = state["options"]
        type = state["type"]
        archive = state.get("isHistory", False)

        # Send the events to the appropriate formatting method
        filter_params = state["params"]["params"]
        del state["params"]["params"]
        params.update(filter_params)
        getattr(self, type)(self.request.response, archive, options, **params)
        # aborting the long running export transaction so it is not retried
        import transaction

        transaction.abort()

    def _get_event_fields(self, event, requested_fields):
        """
        Returns the fields present in the event placing
        requested_events first, details last and rest of
        the fiels in alphabetic order
        """
        returned_fields = set(event.keys())
        header = []
        # Lets put the requested fields first
        if requested_fields:
            for field in requested_fields:
                if field in returned_fields:
                    returned_fields.remove(field)
                header.append(field)
        # returned_fields has the fields that have not been explicitely
        #  requested. lets append them ensuring details are at the end
        show_details = False
        if DETAILS_KEY in returned_fields:
            returned_fields.remove(DETAILS_KEY)
            show_details = True
        not_requested_fields = list(
            sorted(returned_fields, key=lambda x: x.lower())
        )
        if show_details:
            not_requested_fields.append(DETAILS_KEY)
        header.extend(not_requested_fields)

        return header

    def _query(
        self,
        archive,
        uid=None,
        fields=None,
        exportVisible=True,
        sort=None,
        dir=None,
        evids=None,
        excludeIds=None,
        params=None,
    ):
        jsonParams = params
        if isinstance(jsonParams, dict):
            jsonParams = json.dumps(jsonParams)
        zepRouter = EventsRouter(self.context, self.request)
        summaryEvents = zepRouter.queryGenerator(
            archive=archive,
            sort=sort,
            dir=dir,
            evids=evids,
            uid=uid,
            excludeIds=excludeIds,
            params=jsonParams,
            detailFormat=True,
        )
        header = []
        for event in summaryEvents:
            # default values for fields some optional fields in ZEP events
            if isinstance(event.get("DeviceClass"), dict):
                event["DeviceClass"] = event["DeviceClass"]["name"]
            if "device_uuid" in event:
                del event["device_uuid"]

            parsed_details = {
                detail["key"]: detail["value"]
                for detail in event[DETAILS_KEY]
                if detail["key"] not in event
            }
            event[DETAILS_KEY] = parsed_details

            del event["log"]
            if not header:
                header = (
                    fields
                    if exportVisible
                    else self._get_event_fields(event, fields)
                )

            yield header, event

    def _timeformat(self, value, options):
        utc_dt = pytz.utc.localize(datetime.utcfromtimestamp(int(value)))
        tz = pytz.timezone(options["tz"])
        tval = tz.normalize(utc_dt.astimezone(tz))
        if options["fmt"] == "iso":
            return str(tval.isoformat())
        if options["fmt"] == "unix":
            return str(int(value))
        if options["fmt"] == "user":
            return str(
                tval.strftime(
                    convertJsTimeFormatToPy(
                        options["datefmt"] + " " + options["timefmt"]
                    )
                )
            )

    def csv(self, response, archive, options, **params):
        response.setHeader("Content-Type", "application/vns.ms-excel")
        response.setHeader(
            "Content-Disposition", "attachment; filename=events.csv"
        )
        from csv import writer

        writer = writer(response)

        wroteHeader = False
        for fields, evt in self._query(archive, **params):
            data = []
            if not wroteHeader:
                writer.writerow(fields)
                wroteHeader = True
            details = evt.get(DETAILS_KEY)

            for field in fields:
                val = evt.get(field, "")
                if field in ("lastTime", "firstTime", "stateChange") and val:
                    val = self._timeformat(val, options)
                elif field == DETAILS_KEY and val:
                    # ZEN-ZEN-23871: add all details in one column
                    val = json.dumps(val)
                elif not (val or val == 0) and details:
                    # ZEN-27617: fill in value for requested field in details
                    val = details.get(field, "")
                data.append(
                    str(val).replace("\n", " ").strip()
                    if (val or val == 0)
                    else ""
                )
            writer.writerow(data)

    def xml(self, response, archive, options, **params):
        response.setHeader("Content-Type", "text/xml; charset=utf-8")
        response.setHeader(
            "Content-Disposition", "attachment; filename=events.xml"
        )
        from xml.sax.saxutils import escape, quoteattr

        response.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<!-- Common Event Format compliant event structure -->\n"
            "<ZenossEvents>\n"
        )

        evutil = IEventManagerProxy(self)
        zem = evutil.event_manager()
        reporterComponent = (
            "\t<ReporterComponent>\n"
            "\t\t<url>%s</url>\n"
            "\t</ReporterComponent>\n"
        ) % (escape(zem.absolute_url_path()))

        for fields, evt in self._query(archive, **params):
            firstTime = self._timeformat(evt["firstTime"], options)
            response.write(
                "<ZenossEvent ReportTime=%s>\n" % quoteattr(firstTime)
            )
            response.write(
                (
                    "\t<SourceComponent>\n"
                    "\t\t<DeviceClass>%s</DeviceClass>\n"
                    "\t\t<device>%s</device>\n"
                    "\t\t<ipAddress>%s</ipAddress>\n"
                    "\t</SourceComponent>\n"
                )
                % (
                    escape(str(evt.get("DeviceClass", ""))),
                    escape(str(evt.get("device", ""))),
                    escape(str(evt.get("ipAddress", ""))),
                )
            )
            response.write(reporterComponent)
            for tag in ("dedupid", "summary", "message"):
                response.write(
                    "\t<{tag}>{val}</{tag}>\n".format(
                        tag=tag, val=escape(str(evt.pop(tag, "")))
                    )
                )

            details = evt.get(DETAILS_KEY)
            if details:
                evt.update(details)
                del evt[DETAILS_KEY]

            exportVisible = params.get("exportVisible", True)
            evtItems = (
                {
                    k: v
                    for k, v in evt.iteritems()
                    if k in fields and exportVisible
                }
                if exportVisible
                else evt
            )

            for key, value in evtItems.iteritems():
                if value is not None:
                    if key in ("lastTime", "firstTime", "stateChange"):
                        value = self._timeformat(value, options)
                    key = str(key).replace(".", "_")
                    response.write(
                        "\t<%s>%s</%s>\n" % (key, escape(str(value)), key)
                    )

            response.write("</ZenossEvent>\n")

        response.write("</ZenossEvents>\n")
