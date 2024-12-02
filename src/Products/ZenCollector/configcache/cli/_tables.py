##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import, division

import datetime

from itertools import chain


class TablesOutput(object):

    def write(self, *groups):
        for group in groups:
            self._display(
                list(group.rows()),
                group.summary(),
                group.headings(),
                group.hints(),
            )

    def _display(self, rows, summary, headings, hints):
        if not rows and not summary:
            return

        # Transform row values for presentation
        if rows:
            rows = [
                tuple(_xform(value, hint) for value, hint in zip(row, hints))
                for row in sorted(rows, key=lambda x: x[0])
            ]

        # Transform total values for presentation
        if summary:
            if rows:
                summary = tuple(
                    _xform(v, h) for v, h in zip([""] + summary, hints)
                )
            else:
                summary = tuple(
                    _xform(v, h) for v, h in zip(summary, hints)
                )

        # Transform column headers for presentation
        if summary and not rows:
            headings = [hdr.capitalize() for hdr in headings]
        else:
            headings = [hdr.upper() for hdr in headings]

        # Initialize maxwidth values for each column
        maxwidths = [0 for _ in headings]

        if summary and not rows:
            hdrmaxw = max(len(hdr) for hdr in headings)
            maxwidths = [hdrmaxw] * len(headings)
        else:
            for row in rows:
                for idx, (mw, col) in enumerate(zip(maxwidths, row)):
                    maxwidths[idx] = max(mw, len(str(col)))
            for idx, (mw, hd) in enumerate(zip(maxwidths, headings)):
                maxwidths[idx] = max(mw, len(hd))
            for idx, (mw, tv) in enumerate(zip(maxwidths[1:], summary)):
                maxwidths[idx + 1] = max(mw, len(str(tv)))

        offset = len(maxwidths)
        tmplt = "  ".join(
            "{{{0}:{{{1}}}}}".format(idx, idx + offset)
            for idx in range(0, offset)
        )
        fmtspecs = [
            _get_fmt_spec(mw, hint) for mw, hint in zip(maxwidths, hints)
        ]
        print()
        if summary and not rows:
            for hdr, value in zip(headings, summary):
                print("{0:{2}}: {1}".format(hdr, value, maxwidths[0]))
        else:
            if headings:
                print(tmplt.format(*chain(headings, fmtspecs)))
                sep = ["-" * c for c in maxwidths]
                print(tmplt.format(*chain(sep, maxwidths)))

            for row in rows:
                print(tmplt.format(*chain(row, fmtspecs)))

            if summary:
                print(tmplt.format(*chain(sep, maxwidths)))
                print(tmplt.format(*chain(summary, fmtspecs)))


def _xform(value, hint):
    if hint == "timedelta":
        td = datetime.timedelta(seconds=value)
        hours = td.seconds // 3600
        minutes = (td.seconds - (hours * 3600)) // 60
        seconds = td.seconds - (hours * 3600) - (minutes * 60)
        return "{0} {1:02}:{2:02}:{3:02}".format(
            (
                ""
                if td.days == 0
                else "{} day{}".format(td.days, "" if td.days == 1 else "s")
            ),
            hours,
            minutes,
            seconds,
        ).strip()
    else:
        return value


def _get_fmt_spec(mw, hint):
    if hint == "int":
        return ">{}".format(mw)
    elif hint == "timedelta":
        return ">{}".format(mw)
    elif hint == "float":
        return ">{}.2f".format(mw)
    return mw
