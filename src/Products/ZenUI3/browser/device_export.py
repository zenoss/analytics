##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from xml.etree.ElementTree import Element, tostring

from Products.Five.browser import BrowserView

from Products import Zuul
from Products.ZenEvents.EventClass import EventClass
from Products.ZenUtils.jsonutils import unjson
from Products.Zuul.facades.devicefacade import DeviceFacade

log = logging.getLogger("zen.deviceexporter")


def event(values):
    """
    :param values: dictionary with total and acknowledged count for each
        event's severity.
    :return: total count of events with higher severity
    """

    # Get event's types with non-zero value of "count" field
    values = {
        x: y.get("count") for x, y in values.iteritems() if y.get("count")
    }
    if not values:
        return "0"
    # Swap severitie's keys and values
    severities = {x.lower(): y for y, x in EventClass.severities.items()}
    # Get name of highly important event kind in values
    m = max(values, key=severities.__getitem__)
    # Report it
    return str(values[m])


class DeviceExporter(BrowserView):
    def __call__(self):
        body = unjson(self.request.form["body"])
        type = body.get("type")
        getattr(self, type)(
            self.request.response, self._query(body), body["fields"]
        )

    def _query(self, params):
        device_router = DeviceFacade(self.context)
        devices = device_router.getDevices(
            uid=params["uid"],
            sort=params["sort"],
            dir=params["sdir"],
            params=params["params"],
            limit=None,
        )
        return Zuul.marshal(devices.results, params["fields"])

    @staticmethod
    def xml(response, devices, fields):
        response.setHeader("Content-Type", "text/xml; charset=utf-8")
        response.setHeader(
            "Content-Disposition", "attachment; filename=devices.xml"
        )
        response.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        response.write("<ZenosDevices>\n")
        for device in devices:
            xml_device = Element("ZenossDevice")
            for field in fields:
                device_field = Element(field)
                value = device.get(field, "")
                if field == "events":
                    device_field.text = event(value)
                elif field in ["systems", "groups"]:
                    for s in value:
                        sub_field = Element(field[:-1])
                        sub_field.text = str(s.get("name"))
                        device_field.append(sub_field)
                elif isinstance(value, dict):
                    value = value.get("name", "")
                    device_field.text = str(value)
                else:
                    device_field.text = str(value)
                xml_device.append(device_field)
            response.write(tostring(xml_device))
        response.write("")
        response.write("</ZenosDevices>\n")

    @staticmethod
    def csv(response, devices, fields):
        response.setHeader("Content-Type", "application/vns.ms-excel")
        response.setHeader(
            "Content-Disposition", "attachment; filename=devices.csv"
        )
        from csv import writer

        writer = writer(response)
        writer.writerow(fields)
        for device in devices:
            data = []
            for field in fields:
                value = device.get(field, "")
                if isinstance(value, list):
                    value = "|".join([v.get("name") for v in value])
                if isinstance(value, dict):
                    value = (
                        event(value)
                        if field == "events"
                        else value.get("name")
                    )
                if not (value or value == 0):
                    value = ""
                data.append(str(value).strip())
            writer.writerow(data)
