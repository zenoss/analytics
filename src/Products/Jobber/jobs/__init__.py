##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from .job import Job  # noqa: F401
from .facade import FacadeMethodJob  # noqa: F401
from .misc import (  # noqa: F401
    DeviceListJob,
    PausingJob,
    DelayedFailure,
    pause,
)
from .purge_logs import purge_logs  # noqa F401
from .roles import DeviceSetLocalRolesJob  # noqa: F401
from .subprocess import SubprocessJob  # noqa: F401


def _get_all():
    # Return the names of all the celery Task classes
    import inspect
    from celery import Task

    return tuple(
        n
        for n, j in globals().items()
        if inspect.isclass(j) and issubclass(j, Task)
    )


__all__ = _get_all()
del _get_all
