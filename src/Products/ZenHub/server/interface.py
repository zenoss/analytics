##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.component.interfaces import Interface
from zope.interface import Attribute


class IHubServerConfig(Interface):
    """An object providing service manager configuration data."""

    metric_priority_map = Attribute(
        "Maps metric names to ServiceCallPriority values.",
    )

    priorities = Attribute(
        "A sequence containing ServiceCallPriority's priority names.",
    )

    executors = Attribute("Maps worklist names to Executor objects.")

    routes = Attribute("Maps ServiceCalls to worklist names.")

    modeling_pause_timeout = Attribute(
        "Number of seconds to wait before resuming the execution "
        "of ServiceCalls with MODELING priority.",
    )

    task_max_retries = Attribute(
        "Limit the number of times a ServiceCall is retried.",
    )

    pbport = Attribute(
        "The port number the Perspective Broker will listen on.",
    )

    xmlrpcport = Attribute(
        "The port number the XMLRPC server will listen on.",
    )


class IServiceCall(Interface):
    """An object that captures the signature of a ZenHub service call."""

    id = Attribute("Uniquely identifies this instance")  # noqa: A003
    monitor = Attribute("Name of the caller's collection monitor")
    service = Attribute("Name of the service")
    method = Attribute("Name of the method on the service")
    args = Attribute("The positional arguments to the method")
    kwargs = Attribute("The keyword arguments to the method")


class IServiceCallEvent(Interface):
    """Common interface for ServiceCall events.

    All events have the following six fields populated.

    Field      Description
    ---------  ----------------------------------------------------------
    id         Uniquely identifies the service call instance
    monitor    Name of the collector the call originated from
    service    Name of the service to execute method on
    method     Name of the method on the service to execute
    args       Positional arguments to method
    kwargs     Keyword arguments to method
    timestamp  When the event occurred
    queue      Names the queue the service call is a member of
    priority   The priority of the service call
    """

    id = Attribute("Unique identifier for ServiceCall instance")  # noqa: A003
    monitor = Attribute("Name of the monitor")
    service = Attribute("Name of the service")
    method = Attribute("Name of the method on the service")
    args = Attribute("Positional arguments to the method")
    kwargs = Attribute("Keyword arguments to the method")
    timestamp = Attribute("When the event happened")
    queue = Attribute("Name of the executor processing the service call")
    priority = Attribute("Priority of the service call")


class IServiceCallReceivedEvent(IServiceCallEvent):
    """ZenHub has accepted a request to execute a method on a service."""


class IServiceCallStartedEvent(IServiceCallEvent):
    """ZenHub has started executing a method on a service.

    Adds these additional fields:

    Field      Description
    ---------  ----------------------------------------------------------
    worker     Identifies the worker executing the service call
    attempts   Count of the execution attempts (so far)
    """

    worker = Attribute("Worker executing the service call")
    attempts = Attribute("Number of attempts to execute the service call")


class IServiceCallCompletedEvent(IServiceCallStartedEvent):
    """ZenHub has completed executing a method on a service.

    If the call completed successfully, the 'error' and 'retry' fields
    will have None as their values.  If the call failed and ZenHub can
    retry its execution, the 'retry' field is set to the exception that
    caused the failure.  If the call failed and ZenHub cannot retry its
    execution, the 'error' field is set to the exception.

    ----------------------------------------------------
    state   | retryable | result | error     | retry
    --------+-----------+--------+-----------+----------
    success |    n/a    |  Any   | None      | None
    failure |    yes    |  None  | None      | Exception
    failure |    no     |  None  | Exception | None
    ----------------------------------------------------

    Note the 'result' can be None when both 'error' and 'retry' are None.

    Field      Description
    ---------  ----------------------------------------------------------
    timestamp  When the service call finished executing.
    queue      Identifies the executor that executed the service call
    priority   The priority of the service call
    worker     Identifies the worker that executed the service call
    attempts   The number times the service call executed before completing
    error      None or an exception object
    retry      None or an exception object
    result     The value returned from the service call (which could be None)
    """

    retry = Attribute("An exception from executing the service call")
    error = Attribute("An exception from executing the service call")
    result = Attribute("The value returned from the method")


class IServiceCallRouter(Interface):
    """Maps ServiceCall objects to executor objects."""

    def get(call):
        """Return an IServiceExecutor for the given IServiceCall.

        :type call: IServiceCall
        :rtype: IServiceExecutor
        """


class IServiceExecutor(Interface):
    """An object that executes submitted IServiceCall tasks."""

    def submit(servicecall):
        """Submit an IServiceCall for asynchronous execution.

        The returned Deferred object is fired when the call has completed.

        :type servicecall: IServiceCall
        :rtype: twisted.internet.defer.Deferred
        """
