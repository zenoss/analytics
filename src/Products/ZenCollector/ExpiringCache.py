##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import time


class ExpiringCache(object):
    """Cache where entries expire after a defined duration."""

    def __init__(self, seconds):
        """Initialize cache. Set seconds to seconds before expiration."""
        self.seconds = seconds
        self.data = {}
        self.last_cleanse = time.time()

    def update(self, d, asof=None, set_fn=None):
        """Update the cache from a dict of keys and values.
        Specify asof as a time.time()-style timestamp to update as of
        a certain time. Specify set_fn to customize how each key will
        be updated based on old and new timestamps and values.
        """
        if asof is None:
            asof = time.time()

        for key, value in d.iteritems():
            self.set(key, value, asof=asof, set_fn=set_fn)

    def validate(self, key):
        """Returns True if the key is still valid."""
        now = time.time()
        if key not in self.data:
            return False
        added, value = self.data[key]
        if added + self.seconds < now:
            self.invalidate(key)
            return False
        return True

    def __contains__(self, key):
        return self.validate(key)

    def set(self, key, value, asof=None, set_fn=None):
        """Set key to value in cache.
        Specify asof as a time.time()-style timestamp to update as of
        a certain time. Specify set_fn to customize how each key will
        be updated based on old and new timestamps and values.
        """
        if asof is None:
            asof = time.time()

        old = self.data.get(key, (None, None))

        if set_fn:
            new = set_fn(old[0], old[1], asof, value)
        else:
            new = (asof, value)

        if new != old:
            self.data[key] = new

    def get(self, key, default=None):
        """Return current value of key from cache."""
        now = time.time()
        self.cleanse(now)

        try:
            added, value = self.data[key]
            if added + self.seconds < now:
                self.invalidate(key)
                return default
            else:
                return value
        except KeyError:
            return default

    def invalidate(self, key):
        """Remove key from cache."""
        try:
            del self.data[key]
        except Exception:
            pass

    def cleanse(self, asof):
        """Remove all expired entries from cache."""
        if self.last_cleanse + self.seconds < asof:
            self.last_cleanse = asof
            for key, (added, _) in self.data.items():
                if added + self.seconds < asof:
                    self.invalidate(key)

    def values(self):
        """Generate all values in cache."""
        for key in self.data.iterkeys():
            yield self.get(key)
