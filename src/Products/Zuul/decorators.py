##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import functools
from decorator import decorator
from AccessControl import Unauthorized
from Products import Zuul
from Products.ZenUtils.Ext import DirectResponse
from zenoss.protocols.services import ServiceConnectionError, ZepConnectionTimeout
from zenoss.protocols.services.zep import ZepConnectionError

import logging
import threading

log = logging.getLogger("zeneventserver")
attempts = threading.local()

@decorator
def marshal(f, *args, **kwargs):
    result = f(*args, **kwargs)
    return Zuul.marshal(result)


def marshalto(keys=None, marshallerName=''):
    @decorator
    def marshal(f, *args, **kwargs):
        result = f(*args, **kwargs)
        return Zuul.marshal(result, keys=keys, marshallerName=marshallerName)
    return marshal


@decorator
def info(f, *args, **kwargs):
    """
    Apply Zuul.info to results.
    """
    result = f(*args, **kwargs)
    return Zuul.info(result)


def infoto(adapterName=''):
    @decorator
    def info(f, *args, **kwargs):
        result = f(*args, **kwargs)
        return Zuul.info(result, adapterName=adapterName)
    return info


@decorator
def memoize(f, *args, **kwargs):
    sig = repr((args, kwargs))
    cache = f._m_cache = getattr(f, '_m_cache', {})
    if sig not in cache:
        cache[sig] = f(*args, **kwargs)
    return cache[sig]


def require(permission):
    """
    Decorator that checks if the current user has the permission. Only valid on
    IFacade objects.
    """
    @decorator
    def wrapped_fn(f, self, *args, **kwargs):
        if callable(permission):
            if not permission(self, *args, **kwargs):
                args = (f.__name__, permission.__name__)
                raise Unauthorized('Calling %s requires "%s" permission' % args)
            return f(self, *args, **kwargs)
        else:
            if not Zuul.checkPermission(permission, self.context):
                args = (f.__name__, permission)
                raise Unauthorized('Calling %s requires "%s" permission' % args)
            return f(self, *args, **kwargs)
    return wrapped_fn


def keyworddecorator(decorator_func):
    """
    Turns a function into a well-behaved decorator.

    Requires the signature (func, *args, **kwargs).

    Updates the inner function to look like the decorated version by
    copying attributes from the one to the other.

    This passes in the arguments in kwargs which
    the contextRequire decorator requires
    """
    def _decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            return decorator_func(func, *args, **kwargs)
        return inner
    return _decorator

def contextRequire(permission, contextKeywordArgument):
    """
    Decorator that checks if the current user has the permission on a passed in context.
    The argument can be either the unique string of an object (uid) or the object itself.

    NOTE: This decorator assumes that the arguments to the method will be passed
    in as keyword arguments.  It is mainly used by the routers where this is the
    case.
    """
    @keyworddecorator
    def wrapped_fn(f, self, *args, **kwargs):
        context = kwargs[contextKeywordArgument]
        if isinstance(context, basestring):
            context = self.context.unrestrictedTraverse(context)
        if not Zuul.checkPermission(permission, context):
            args = (f.__name__, permission)
            raise Unauthorized('Calling %s requires "%s" permission.' % args)
        return f(self, *args, **kwargs)
    return wrapped_fn

@decorator
def serviceConnectionError(func, *args, **kwargs):
    count = getattr(attempts, 'value', 0)
    try:
        f = func(*args, **kwargs)
        setattr(attempts, 'value', 0)
        return f
    except ZepConnectionTimeout as e:
        log.warn('Connection to zeneventserver timed out.')
        msg = 'Connection to zeneventserver timed out, please try again.'
    except ZepConnectionError as e:
        count += 1
        setattr(attempts, 'value', count)
        log.warn('Connection refused. Check zeneventserver status on Services. Exception on thread: %s', threading.current_thread().ident)
        if count >= 10:
            msg = 'Connection refused. Check zeneventserver status on <a href="zport/dmd/daemons">Services</a>'
            setattr(attempts, 'value', 0)
        else:
            return
    except ServiceConnectionError as e:
        msg = 'Connection refused to a required daemon. Check status on <a href="zport/dmd/daemons">Services</a>'
    return DirectResponse.fail(msg, sticky=True)
