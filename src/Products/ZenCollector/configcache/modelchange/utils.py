##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from functools import wraps as _wraps

import six as _six


def coroutine(func):
    """Decorator for initializing a generator as a coroutine."""

    @_wraps(func)
    def start(*args, **kw):
        coro = func(*args, **kw)
        coro.next()
        return coro

    return start


def into_tuple(args):
    if isinstance(args, _six.string_types):
        return (args,)
    elif not hasattr(args, "__iter__"):
        return (args,)
    return args
