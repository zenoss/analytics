##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import traceback

from Products.ZenEvents.ZenEventClasses import Critical


def trapException(service, functor, *args, **kwargs):
    """
    Call the functor using the arguments and trap unhandled exceptions.

    :parameter functor: function to call.
    :type functor: Callable[Any, Any]
    :parameter args: positional arguments to functor.
    :type args: Sequence[Any]
    :parameter kwargs: keyword arguments to functor.
    :type kwargs: Map[Any, Any]
    :returns: result of calling functor(*args, **kwargs)
        or None if functor raises an exception.
    :rtype: Any
    """
    try:
        return functor(*args, **kwargs)
    except Exception as ex:
        msg = "Unhandled exception in zenhub service %s: %s" % (
            service.__class__,
            ex,
        )
        service.log.exception(msg)
        service.sendEvent(
            {
                "severity": Critical,
                "component": str(service.__class__),
                "traceback": traceback.format_exc(),
                "summary": msg,
                "device": service.instance,
                "methodCall": "%s(%s, %s)" % (functor.__name__, args, kwargs),
            }
        )
