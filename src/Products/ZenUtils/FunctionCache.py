###########################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
###########################################################################

import hashlib
import memcache
import operator
import cPickle as pickle

import logging 
_LOG = logging.getLogger("zen.zenutils.functioncache")

from zope.component import getGlobalSiteManager

CACHE_NOT_FOUND = object()

class FunctionCache(object):
    """
    FunctionCache is a decorator that will cache the results of the
    wrapped function based on its parameters. It's functionally
    equivalent to @memoize but uses a memcached backend. The value
    returned by the decorated function should return back a serializable
    value.
    """

    _CACHE_CLIENT = None
    _CONFIG = None

    def __init__(self, cache_key, default_timeout=None, cache_miss_marker=None):
        self._cache_key = cache_key
        self._default_timeout = default_timeout
        self._mc = None
        self._cache_miss_marker = cache_miss_marker

    def _init_cache(self):
        _LOG.info("initializing FunctionCache")
        client, timeout = self.getCacheClient()
        if client is None:
            self._mc = CACHE_NOT_FOUND
            return
        self._mc = client
        if timeout:
            self._add_args = [timeout,]
        else:
            self._add_args = []

    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            if self._mc is None:
                self._init_cache()

            if self._mc is CACHE_NOT_FOUND:
                return f(*args, **kwargs)

            hashKey = _compose_key(self._cache_key, args, kwargs)

            value = self._mc.get(hashKey)
            if value:
                value = pickle.loads(value)
            if self._cache_miss_marker is not None:
                if value == self._cache_miss_marker:
                    value = None
                elif value is None:
                    value = f(*args, **kwargs)
                    _LOG.debug("caching lookup for %r: hashKey=%s, value=%s, "
                            "self._cache_miss_marker=%s" % \
                            (f, hashKey, value, self._cache_miss_marker))
                    valueToPickle = value if value is not None \
                            else self._cache_miss_marker
                    self._mc.add(hashKey, pickle.dumps(valueToPickle),
                            *self._add_args)
            elif value is None:
                value = f(*args, **kwargs)
                if value is not None:
                    _LOG.debug("caching lookup for %r: hashKey=%s, value=%s" % \
                            (f, hashKey, value))
                    self._mc.add(hashKey, pickle.dumps(value), *self._add_args)

            return value
        return wrapped_f

    def getCacheClient(self):
        """
        getCacheClient returns a tuple (cache_client, timeout) for the given
        cache_key. The key is looked up in global.conf. If the application
        cache servers are not set or the cache_key is not found a (None, None)
        is returned.
        """
        if FunctionCache._CACHE_CLIENT == False:
            return None, None

        if FunctionCache._CONFIG is None:
            from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
            FunctionCache._CONFIG = getGlobalConfiguration()

        if FunctionCache._CACHE_CLIENT is None:
            if 'applicationcache' in FunctionCache._CONFIG:
                FunctionCache._CACHE_CLIENT = memcache.Client(
                        FunctionCache._CONFIG['applicationcache'].split(","))
            elif 'zodb-cacheservers' in FunctionCache._CONFIG:
                FunctionCache._CACHE_CLIENT = memcache.Client(
                        FunctionCache._CONFIG['zodb-cacheservers'].split(","))
            else:
                FunctionCache._CACHE_CLIENT = False

        config_key = "applicationcache_%s" % self._cache_key
        if config_key in FunctionCache._CONFIG and FunctionCache._CACHE_CLIENT:
            try:
                return (FunctionCache._CACHE_CLIENT,
                        int(FunctionCache._CONFIG[config_key]))
            except ValueError:
                _LOG.warn("config_key %s found but value did not parse: %s" % \
                        (config_key, FunctionCache._CONFIG[config_key]))

        if FunctionCache._CACHE_CLIENT:
            if self._default_timeout is None:
                return FunctionCache._CACHE_CLIENT, None
            return FunctionCache._CACHE_CLIENT, int(self._default_timeout)

        return None, None

def _compose_key(_cache_key, args, kwargs):
    arglist = [_cache_key,]
    for arg in args:
        arglist.append(arg)
    for key, value in sorted(kwargs.iteritems(), key=operator.itemgetter(1)):
        arglist.append((key, value,))
    hashKey = "FC|%s" % (hashlib.sha1(repr(arglist)).hexdigest())
    return hashKey

if __name__=='__main__':

    @FunctionCache(cache_key='foobar')
    def foo(arg):
        return arg + 10

    print foo(30)

