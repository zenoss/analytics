##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from inspect import getargspec


def fun_takes_kwargs(fun, kwlist=[]):
    """With a function, and a list of keyword arguments, returns arguments
    in the list which the function takes.
    If the object has an `argspec` attribute that is used instead
    of using the :meth:`inspect.getargspec` introspection.
    :param fun: The function to inspect arguments of.
    :param kwlist: The list of keyword arguments.
    Examples
        >>> def foo(self, x, y, logfile=None, loglevel=None):
        ...     return x * y
        >>> fun_takes_kwargs(foo, ['logfile', 'loglevel', 'task_id'])
        ['logfile', 'loglevel']
        >>> def foo(self, x, y, **kwargs):
        >>> fun_takes_kwargs(foo, ['logfile', 'loglevel', 'task_id'])
        ['logfile', 'loglevel', 'task_id']
    """

    S = getattr(fun, 'argspec', getargspec(fun))
    if S.keywords is not None:
        return kwlist
    return [kw for kw in kwlist if kw in S.args]
