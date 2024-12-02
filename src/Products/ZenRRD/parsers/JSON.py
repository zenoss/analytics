##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""JSON

General purpose JSON parser for handling JSON objects matching the following
template. This allows many datapoints for many components to be collected
from a single COMMAND datasource. It also allows for collection of many
events from a single COMMAND datasource.

{
    "values": {
        "component_id_1": {
            "datapoint1": 123.4,
            "datapoint2": 987.6
        },

        "component_id_2": {
            "datapoint1": 56.7,
            "datapoint2": 54.3
        }
    },

    "events": [
        {
            "severity": 2,
            "other_field_1": "value for other field",
            "summary": "event summary"
        },

        {
            "severity": 3,
            "other_field_1": "another value for other field",
            "summary": "another event summary"
        }
    ]
}

"""

import json
import logging

from Products.ZenRRD.CommandParser import CommandParser

log = logging.getLogger("zen.json")


def stringify_keys(dictionary):
    """Convert all keys of given dictionary to strings.

    During serialization and deserialization between the collector and hub we
    need to enforce that dictionary keys are plan, not unicode, strings.

    """
    fixed_dictionary = {}
    for k, v in dictionary.items():
        fixed_dictionary[str(k)] = v

    return fixed_dictionary


class JSON(CommandParser):
    def processResults(self, cmd, result):
        data = None

        try:
            data = json.loads(cmd.result.output)
        except Exception as ex:
            # See NOTE below. If this event ever occurs it will not auto-clear.
            result.events.append(
                {
                    "severity": cmd.severity,
                    "summary": "error parsing command output",
                    "eventKey": cmd.eventKey,
                    "eventClass": cmd.eventClass,
                    "command_output": cmd.result.output,
                    "exception": str(ex),
                }
            )

            return

        # NOTE: It might be a good idea to send a clear event for the potential
        # parse error above. However, this would end up flooding clear events
        # that are almost always useless. I've chosen to trust the executed
        # plugin to always return JSON data of some sort.

        # Pass incoming events straight through.
        result.events.extend(map(stringify_keys, data.get("events", [])))

        # Map incoming values to their components and datapoints.
        if len(data.get("values", {}).keys()) > 0:
            for point in cmd.points:
                if point.component not in data["values"]:
                    continue

                if point.id not in data["values"][point.component]:
                    log.debug(
                        "No matches found in parsed data for "
                        "datasource '%s.%s'",
                        point.id,
                        cmd.ds,
                    )
                    continue

                result.values.append(
                    (point, data["values"][point.component][point.id])
                )

        return result
