##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import zope.i18n

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.i18nmessageid import MessageFactory

from Products.ZenUI3.browser.eventconsole.columns import (
    ARCHIVE_COLUMN_CONFIG,
    COLUMN_CONFIG,
    DEFAULT_COLUMN_ORDER,
    DEFAULT_COLUMNS,
)
from Products.ZenUI3.utils.javascript import JavaScriptSnippet
from Products.ZenUtils.jsonutils import JavaScript, javascript
from Products.Zuul import getFacade
from zenoss.protocols.protobufs.zep_pb2 import EventDetailItem
from zenoss.protocols.services.zep import ZepConnectionError

_ = MessageFactory("zenoss")

log = logging.getLogger("zep.grid")


class EventConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile("view-events.pt")


class HistoryConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile("view-history-events.pt")


def _find_column_fields():
    """
    Given a list of event details that are being indexed by ZEP,
    add any custom fields to the default column list.

    TODO: We need to map these details to the old property names.
    """
    try:
        details = getFacade("zep").getUnmappedDetails()
        for item in details:
            if item["key"] not in DEFAULT_COLUMN_ORDER:
                DEFAULT_COLUMN_ORDER.append(item["key"])
    except ZepConnectionError as e:
        log.error(e.message)

    return DEFAULT_COLUMN_ORDER


def _find_column_definitions(archive=False):
    """
    Given a list of event details that are being indexed by ZEP,
    add any custom fields to the list of column definitions.

    TODO: We need to map these details to the old property names.
    """

    columns = COLUMN_CONFIG
    if archive:
        columns = ARCHIVE_COLUMN_CONFIG

    try:
        details = getFacade("zep").getUnmappedDetails()
    except ZepConnectionError as e:
        log.error(e.message)
        return columns

    for item in details:
        # add or update anything that already exists in our column definition
        # with the result from ZEP. This will override known columns and create
        # new column definitions for new custom fields. The id for these
        # columns is implied from the key used to store in columns.
        detailConfig = {
            "header": item["name"],
            "filter": {"xtype": "textfield"},
            "sortable": True,
        }

        if item["type"] in (EventDetailItem.INTEGER, EventDetailItem.LONG):
            detailConfig["filter"]["vtype"] = "numrange"
        elif item["type"] in (EventDetailItem.DOUBLE, EventDetailItem.FLOAT):
            detailConfig["filter"]["vtype"] = "floatrange"

        columns[item["key"]] = detailConfig

    return columns


def reader_config(archive=False):
    columns = _find_column_definitions(archive)

    readerFields = []
    fields = _find_column_fields()
    for field in fields:
        # If the column definition also has a property for defining the field
        # on the reader, use that. If not, we have to just use the defaults.
        if "field_definition" in columns[field]:
            col = JavaScript(columns[field]["field_definition"])
        else:
            col = dict(name=field)
        readerFields.append(javascript(col))
    return readerFields


def column_config(request=None, archive=False):
    columns = _find_column_definitions(archive)

    column_definitions = []
    fields = _find_column_fields()
    for field in fields:
        col = columns[field].copy()
        if request:
            msg = _(col["header"])
            col["header"] = zope.i18n.translate(msg, context=request)
        col["id"] = field.replace(".", "_")
        if "dataIndex" not in col:
            col["dataIndex"] = field
        col["filterKey"] = field
        if isinstance(col["filter"], basestring):
            col["filter"] = {"xtype": col["filter"]}
        col["sortable"] = col.get("sortable", False)
        col["hidden"] = col.get("hidden", field not in DEFAULT_COLUMNS)

        if "renderer" in col:
            col["renderer"] = JavaScript(col["renderer"])

        column_definitions.append(javascript(col))
    return column_definitions


class EventClasses(JavaScriptSnippet):
    def snippet(self):
        paths = self.context.dmd.Events.getOrganizerNames()
        return (
            """
        Ext.onReady(function(){
            Zenoss.env.EVENT_CLASSES = %s;
        })
        """
            % paths
        )


class GridColumnDefinitions(JavaScriptSnippet):
    def snippet(self):
        last_path_item = self.request["PATH_INFO"].split("/")[-1]
        archive = (
            last_path_item.lower().find("history") != -1
            or last_path_item.lower().find("archive") != -1
        )

        result = ["Ext.onReady(function(){"]

        defs = column_config(self.request, archive=archive)

        reader_fields = reader_config(archive=archive)

        result.append("Zenoss.env.COLUMN_DEFINITIONS=[")
        result.append(",\n".join(defs))
        result.append("];")

        result.append("Zenoss.env.READER_DEFINITIONS=[")
        result.append(",\n".join(reader_fields))
        result.append("];")

        result.append("Zenoss.env.ZP_DETAILS=[")
        try:
            zepdetails = getFacade("zep").getUnmappedDetails()
            zpdetails = []
            for detail in zepdetails:
                if detail["type"] in (
                    EventDetailItem.STRING,
                    EventDetailItem.IP_ADDRESS,
                    EventDetailItem.PATH,
                ):
                    rulecmp = "Zenoss.form.rule.STRINGCOMPARISONS"
                else:
                    rulecmp = "Zenoss.form.rule.NUMBERCOMPARISONS"
                zpdetails.append(
                    "{{ text: _t('{name}'), value: '{key}', "
                    "comparisons: {cmp} }}".format(
                        name=detail["name"], key=detail["key"], cmp=rulecmp
                    )
                )
            result.append(",\n".join(zpdetails))
        except ZepConnectionError as e:
            log.error(e.message)
        result.append("];")

        result.append("Zenoss.env.EVENT_AUTO_EXPAND_COLUMN='summary';")

        result.append(
            """

        Ext.define('Zenoss.events.Model',  {
            extend: 'Ext.data.Model',
            idProperty: 'evid',
            fields: Zenoss.env.READER_DEFINITIONS
        });

"""
        )
        result.append("});")
        return "\n".join(result)
