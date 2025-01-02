##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import


def _patchstate():
    from celery import states
    from celery.contrib.abortable import ABORTED

    # Update the state groups to include ABORTED
    groupings = (
        "PROPAGATE_STATES",
        "EXCEPTION_STATES",
        "READY_STATES",
        "ALL_STATES",
    )
    for attr in groupings:
        setattr(states, attr, frozenset({ABORTED} | getattr(states, attr)))
    states.ABORTED = ABORTED

    # Update the PRECENDENCE stuff to account for ABORTED
    offset = states.PRECEDENCE.index(None)
    states.PRECEDENCE.insert(offset, ABORTED)
    states.PRECEDENCE_LOOKUP = dict(
        zip(
            states.PRECEDENCE,
            range(0, len(states.PRECEDENCE)),
        )
    )


_patchstate()
del _patchstate
