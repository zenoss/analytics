##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import attr

from attr.validators import instance_of
from zope.interface import implementer

from ..interfaces import IServiceAddedEvent
from .interface import (
    IServiceCallReceivedEvent,
    IServiceCallStartedEvent,
    IServiceCallCompletedEvent,
)
from .priority import ServiceCallPriority
from .utils import UNSPECIFIED as _UNSPECIFIED


@implementer(IServiceAddedEvent)
class ServiceAddedEvent(object):
    """An event class dispatched when a service is first loaded."""

    def __init__(self, name, instance):
        """Initialize a ServiceAddedEvent instance.

        @param name {str} Name of the service.
        @param instance {str} Name of the performance monitor (collector).
        """
        self.name = name
        self.instance = instance


class ReportWorkerStatus(object):
    """An event to signal zenhubworkers to report their status."""


@attr.s(slots=True, frozen=True)
class _ReceivedData(object):
    id = attr.ib(converter=str)
    monitor = attr.ib(converter=str)
    service = attr.ib(converter=str)
    method = attr.ib(converter=str)
    args = attr.ib()
    kwargs = attr.ib()
    timestamp = attr.ib(validator=instance_of(float))
    queue = attr.ib()
    priority = attr.ib(validator=instance_of(ServiceCallPriority))


@attr.s(slots=True, frozen=True)
class _StartedData(_ReceivedData):
    worker = attr.ib(converter=str)
    attempts = attr.ib(converter=int)

    @attempts.validator
    def _non_zero(self, attribute, value):
        if value < 1:
            raise ValueError("attempts must be an integer greater than zero")


@attr.s(slots=True, frozen=True)
class _CompletedData(_StartedData):
    retry = attr.ib(default=_UNSPECIFIED)
    error = attr.ib(default=_UNSPECIFIED)
    result = attr.ib(default=_UNSPECIFIED)

    def __attrs_post_init__(self):
        unspecified = tuple(
            name
            for name in ("result", "error", "retry")
            if getattr(self, name) is _UNSPECIFIED 
        )
        if len(unspecified) != 2:
            raise TypeError(
                "At least one of fields 'result', 'retry', and 'error' "
                "must be given an argument"
            )
        for name in unspecified:
            object.__setattr__(self, name, None)


@implementer(IServiceCallReceivedEvent)
class ServiceCallReceived(_ReceivedData):
    """ZenHub has accepted a request to execute a method on a service."""


@implementer(IServiceCallStartedEvent)
class ServiceCallStarted(_StartedData):
    """ZenHub has started executing a method on a service."""


@implementer(IServiceCallCompletedEvent)
class ServiceCallCompleted(_CompletedData):
    """ZenHub has completed executing a method on a service."""
