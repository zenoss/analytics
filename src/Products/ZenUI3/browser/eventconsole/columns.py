##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
This module describes the parameters for columns that may appear in the event
console. This is used both to generate the JavaScript defining the columns and
to evaluate filters.
"""

import copy

from zenoss.protocols.protobufs.zep_pb2 import (
    SEVERITY_CLEAR,
    SEVERITY_CRITICAL,
    SEVERITY_DEBUG,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STATUS_ACKNOWLEDGED,
    STATUS_AGED,
    STATUS_CLEARED,
    STATUS_CLOSED,
    STATUS_NEW,
    STATUS_SUPPRESSED,
)


__doc__ = """
The COLUMN_CONFIG dictionary contains the full definitions for all of
the columns that show up in grids. The following definition covers all
of the 'base' Zenoss properties. This dictionary is augmented later to
add any new or custom fields that ZenPacks provide. When new event
details are added via zenpacks, they will show up as custom details.

These details are added to the grid with the following specifications:

    header = item.name
    filter = 'textfield' # or False if not filterable
    sortable = True


The 'id' and 'dataIndex' properties of each column are taken from the
string in the DEFAULT_COLUMN_ORDER list. The key in the COLUMN_CONFIG
dictionary should match one of these entries exactly. When columns are
being parsed, the following properties are supported:

    sortable    : Defaults to False.
    hidden      : Defaults to False if not present in the DEFAULT_COLUMNS
                  list.
    filter      : If present, will be rendered as: `{'xtype': filter}`.
    renderer    : If present, it is expected to be a Javascript class.

The definitions for columns may also specify a 'field_definition' column
that specifies how the field is parsed in the UI. This should be a json
object string like the following:

    field_definition= "{name:'stateChange', type:'date', dateFormat: Zenoss.date.ISO8601Long}"

"""  # noqa E501

COLUMN_CONFIG = {
    "evid": dict(header="Event ID", filter="textfield", sortable=True),
    "dedupid": dict(
        header="Fingerprint",
        filter="textfield",
        sortable=True,
    ),
    "eventState": dict(
        header="Status",
        width=60,
        sortable=True,
        filter={
            "xtype": "multiselectmenu",
            "text": "...",
            "cls": "x-btn x-btn-default-toolbar-small",
            "source": [
                {"value": STATUS_NEW, "name": "New"},
                {"value": STATUS_ACKNOWLEDGED, "name": "Acknowledged"},
                {
                    "value": STATUS_SUPPRESSED,
                    "name": "Suppressed",
                    "checked": False,
                },
                {"value": STATUS_CLOSED, "name": "Closed", "checked": False},
                {"value": STATUS_CLEARED, "name": "Cleared", "checked": False},
                {"value": STATUS_AGED, "name": "Aged", "checked": False},
            ],
        },
        renderer="Zenoss.util.render_status",
    ),
    "severity": dict(
        header="Severity",
        width=60,
        sortable=True,
        filter={
            "xtype": "multiselectmenu",
            "text": "...",
            "cls": "x-btn x-btn-default-toolbar-small",
            "source": [
                {"value": SEVERITY_CRITICAL, "name": "Critical"},
                {"value": SEVERITY_ERROR, "name": "Error"},
                {"value": SEVERITY_WARNING, "name": "Warning"},
                {"value": SEVERITY_INFO, "name": "Info"},
                {"value": SEVERITY_DEBUG, "name": "Debug", "checked": False},
                {"value": SEVERITY_CLEAR, "name": "Clear", "checked": False},
            ],
        },
        renderer="Zenoss.util.render_severity",
        field_definition="{name:'severity',type:'int'}",
    ),
    "device": dict(
        header="Resource",
        filter="textfield",
        renderer="Zenoss.render.linkFromGrid",
        sortable=True,
    ),
    "component": dict(
        header="Component",
        filter="textfield",
        renderer="Zenoss.render.linkFromGrid",
        width=80,
        sortable=True,
    ),
    "eventClass": dict(
        header="Event Class",
        filter={"xtype": "eventclass", "forceSelection": False},
        width=80,
        renderer="Zenoss.render.linkFromGrid",
        sortable=True,
    ),
    "summary": dict(
        header="Summary",
        flex=1,
        filter="textfield",
        renderer="Zenoss.render.eventSummaryRow",
        sortable=True,
    ),
    "firstTime": dict(
        header="First Seen",
        sortable=True,
        filter={
            "xtype": "daterange",
            "format": "Y-m-d H:i:s",
            "invalidText": (
                "{0} is not a valid date - "
                "it must be in the format yyyy/mm/dd hh:mm:ss"
            ),
            "altFormats": (
                "m/d/Y|n/j/Y|n/j/y|m/j/y|n/d/y|m/j/Y|n/d/Y|"
                "m-d-y|m-d-Y|m/d|m-d|md|mdy|mdY|d|Y-m-d|"
                "n-j|n/j|Y-m-d H:i:s \\T\\O Y-m-d H:i:s"
            ),
        },
        width=135,
        renderer="Zenoss.date.renderDateColumn()",
    ),
    "lastTime": dict(
        header="Last Seen",
        sortable=True,
        filter={
            "xtype": "daterange",
            "format": "Y-m-d H:i:s",
            "invalidText": (
                "{0} is not a valid date - "
                "it must be in the format yyyy/mm/dd hh:mm:ss"
            ),
            "altFormats": (
                "m/d/Y|n/j/Y|n/j/y|m/j/y|n/d/y|m/j/Y|n/d/Y|"
                "m-d-y|m-d-Y|m/d|m-d|md|mdy|mdY|d|Y-m-d|"
                "n-j|n/j|Y-m-d H:i:s \\T\\O Y-m-d H:i:s"
            ),
        },
        width=135,
        renderer="Zenoss.date.renderDateColumn()",
    ),
    "count": dict(
        header="Count",
        sortable=True,
        width=60,
        align="right",
        filter={"xtype": "textfield", "vtype": "numrange"},
        field_definition="{name:'count',type:'int'}",
    ),
    "prodState": dict(
        header="Production State",
        sortable=True,
        filter={"xtype": "multiselect-prodstate"},
    ),
    "DevicePriority": dict(
        header="Device Priority",
        sortable=True,
        filter={"xtype": "multiselect-devicepriority"},
    ),
    "stateChange": dict(
        header="State Change",
        sortable=True,
        filter={
            "xtype": "daterange",
            "format": "Y-m-d H:i:s",
            "invalidText": (
                "{0} is not a valid date - "
                "it must be in the format yyyy/mm/dd hh:mm:ss"
            ),
            "altFormats": (
                "m/d/Y|n/j/Y|n/j/y|m/j/y|n/d/y|m/j/Y|n/d/Y|"
                "m-d-y|m-d-Y|m/d|m-d|md|mdy|mdY|d|Y-m-d|"
                "n-j|n/j|Y-m-d H:i:s \\T\\O Y-m-d H:i:s"
            ),
        },
        width=120,
        renderer="Zenoss.date.renderDateColumn()",
    ),
    "eventClassKey": dict(
        header="Event Class Key", filter="textfield", sortable=True
    ),
    "eventGroup": dict(
        header="Event Group", filter="textfield", sortable=True
    ),
    "eventKey": dict(header="Event Key", filter="textfield", sortable=True),
    "agent": dict(header="Agent", filter="textfield", sortable=True),
    "monitor": dict(header="Collector", filter="textfield", sortable=True),
    "ownerid": dict(header="Owner", filter="textfield", sortable=True),
    "facility": dict(header="Syslog Facility", sortable=False, filter=False),
    "priority": dict(header="Syslog Priority", sortable=False, filter=False),
    "eventClassMapping": dict(
        header="Event Class Mapping",
        sortable=False,
        filter=False,
        renderer="Zenoss.render.LinkFromGridGuidGroup",
    ),
    "clearid": dict(header="Cleared by Event ID", filter=False),
    "ntevid": dict(header="NT Event Code", sortable=False, filter=False),
    "ipAddress": dict(header="IP Address", sortable=True, filter="textfield"),
    "message": dict(
        header="Message",
        renderer="Zenoss.render.eventSummaryRow",
        sortable=False,
        filter="textfield",
    ),
    "Location": dict(
        header="Location",
        sortable=True,
        filter="textfield",
        renderer="Zenoss.render.LinkFromGridUidGroup",
    ),
    "DeviceGroups": dict(
        header="Groups",
        sortable=True,
        filter="textfield",
        renderer="Zenoss.render.LinkFromGridUidGroup",
    ),
    "Systems": dict(
        header="Systems",
        sortable=True,
        filter="textfield",
        renderer="Zenoss.render.LinkFromGridUidGroup",
    ),
    "DeviceClass": dict(
        header="Device Class",
        sortable=True,
        filter="textfield",
        renderer="Zenoss.render.LinkFromGridUidGroup",
    ),
}

COLUMN_CONFIG["eventStateText"] = dict(
    dataIndex="eventState",
    header="Status Text",
    width=100,
    filter=COLUMN_CONFIG["eventState"]["filter"],
    renderer="Zenoss.util.render_status_text",
)

ARCHIVE_COLUMN_CONFIG = copy.deepcopy(COLUMN_CONFIG)
ARCHIVE_COLUMN_CONFIG["eventState"]["filter"] = {
    "xtype": "multiselectmenu",
    "text": "...",
    "cls": "x-btn x-btn-default-toolbar-small",
    "source": [
        {
            "value": STATUS_CLOSED,
            "name": "Closed",
        },
        {
            "value": STATUS_CLEARED,
            "name": "Cleared",
        },
        {
            "value": STATUS_AGED,
            "name": "Aged",
        },
    ],
}

ARCHIVE_COLUMN_CONFIG["severity"]["filter"] = {
    "xtype": "multiselectmenu",
    "text": "...",
    "cls": "x-btn x-btn-default-toolbar-small",
    "source": [
        {"value": SEVERITY_CRITICAL, "name": "Critical"},
        {"value": SEVERITY_ERROR, "name": "Error"},
        {"value": SEVERITY_WARNING, "name": "Warning"},
        {"value": SEVERITY_INFO, "name": "Info"},
        {"value": SEVERITY_DEBUG, "name": "Debug", "checked": False},
        {
            "value": SEVERITY_CLEAR,
            "name": "Clear",
        },
    ],
}

DEFAULT_COLUMNS = [
    "eventState",
    "severity",
    "device",
    "component",
    "eventClass",
    "summary",
    "firstTime",
    "lastTime",
    "count",
]

DEFAULT_COLUMN_ORDER = [
    "evid",
    "dedupid",
    "eventState",
    "eventStateText",
    "severity",
    "device",
    "component",
    "eventClass",
    "summary",
    "firstTime",
    "lastTime",
    "count",
    "prodState",
    "DevicePriority",
    "stateChange",
    "eventClassKey",
    "eventGroup",
    "eventKey",
    "agent",
    "monitor",
    "ownerid",
    "facility",
    "priority",
    "eventClassMapping",
    "clearid",
    "ntevid",
    "ipAddress",
    "message",
    "Location",
    "DeviceGroups",
    "Systems",
    "DeviceClass",
]
