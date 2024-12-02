##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import, division

import json


class JSONOutput(object):
    """
    {
        "devices": [
            "summary" : {
                "number_of_devices": 4,
                ...
            }
        ],
        "services": {
            "data": [
                {<column-name>: <value>, ... }, ...
            ],
            "summary": {
                <column-name>: <value>,  # except first column
                ...
            }
        },
        "monitors": {
            "data": [
                {<column-name>: <value>, ... }, ...
            ],
            "summary": {
                <column-name>: <value>,  # except first column
                ...
            }
        },
        "statuses": {
            "data": [
                {<column-name>: <value>, ... }, ...
            ],
            "summary": {
                <column-name>: <value>,  # except first column
                ...
            }
        }
    }
    """

    def write(self, *groups):
        result = {}
        for group in groups:
            rows = list(group.rows())
            summary = group.summary()
            headings = [
                hdr.replace(" ", "_").lower() for hdr in group.headings()
            ]

            if len(rows) == 0 and len(summary) == 0:
                continue

            if len(headings) == 1 and len(rows) == 1:
                result[group.name] = [
                    {headings[0].replace(" ", "_").lower(): rows[0][0]}
                ]
                continue

            rows = [dict(zip(headings, row)) for row in rows]
            if len(rows) == 0:
                summary = dict(zip(headings, summary))
            else:
                summary = dict(zip(headings[1:], summary))
            result[group.name] = {"data": rows, "summary": summary}
        print(json.dumps(result))
