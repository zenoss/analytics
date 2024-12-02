##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time

import attr

from twisted.internet import defer
from zope.component import getUtility
from zope.event import notify

from Products.Zuul.interfaces import IDataRootFactory

from ..events import (
    ServiceCallReceived,
    ServiceCallStarted,
    ServiceCallCompleted,
)
from ..priority import servicecall_priority_map


class SendEventExecutor(object):
    """Executes sendEvent and sendEvents tasks.

    This executor bypasses the EventService and executes the sendEvent
    and sendEvents tasks directly on a MySqlEventManager instance.
    """

    @classmethod
    def create(cls, name, **ignored):
        """Return a new executor instance.

        :param str name: The executor's name
        :return: A new SendEventExecutor instance.
        """
        return cls(name)

    def __init__(self, name):
        """Initialize an SendEventExecutor instance.

        :param str name: the name of this executor
        """
        self.__name = name
        self.__zem = getUtility(IDataRootFactory)().ZenEventManager

    @property
    def name(self):
        return self.__name

    def start(self, reactor):
        pass

    def stop(self):
        pass

    def submit(self, call):
        """Submit a ServiceCall for execution.

        Returns a deferred that will fire when execution completes.
        """
        if call.method not in ("sendEvent", "sendEvents"):
            return defer.fail(
                TypeError(
                    "%s does support executing method '%s'"
                    % (type(self).__name__, call.method),
                )
            )
        method = getattr(self.__zem, call.method, None)
        if method is None:
            return defer.fail(
                AttributeError(
                    "%s has no method '%s'"
                    % (self.__zem.__class__.__name__, call.method),
                )
            )

        # Build args for events
        ctx = attr.asdict(call)
        ctx.update(
            {
                "queue": self.__name,
                "priority": servicecall_priority_map.get(
                    (call.service, call.method)
                ),
            }
        )

        _notify_listeners(ctx, ServiceCallReceived)

        try:
            ctx.update({"worker": "zenhub", "attempts": 1})
            _notify_listeners(ctx, ServiceCallStarted)

            state = method(*call.args, **call.kwargs)
        except Exception as ex:
            ctx.update({"attempts": 1, "error": ex})
            _notify_listeners(ctx, ServiceCallCompleted)
            return defer.fail(ex)
        else:
            ctx.update({"attempts": 1, "result": state})
            _notify_listeners(ctx, ServiceCallCompleted)
            return defer.succeed(state)


def _notify_listeners(ctx, event_class):
    args = dict(ctx)
    args["timestamp"] = time.time()
    event = event_class(**args)
    notify(event)
