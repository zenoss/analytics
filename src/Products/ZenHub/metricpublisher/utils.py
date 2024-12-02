##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import base64
import eventlet
import logging
import string

from functools import wraps

log = logging.getLogger("zen.publisher")


def exponential_backoff(
    exception, delay=0.1, maxdelay=5, sleepfunc=eventlet.sleep
):
    def decorator(f):
        @wraps(f)
        def inner(*args, **kwargs):
            mdelay = delay  # local copy
            failures = 0
            while True:
                try:
                    return f(*args, **kwargs)
                except exception:
                    failures += 1
                    slots = ((2 ** failures) - 1) / 2.0
                    mdelay = min(max(slots * mdelay, mdelay), maxdelay)
                    sleepfunc(mdelay)

        return inner

    return decorator


def basic_auth_string(username, password):
    """
    Creates base64 encoded basic auth token with header
    """
    return "Authorization: " + basic_auth_string_content(username, password)


def basic_auth_string_content(username, password):
    """
    Creates base64 encoded basic auth token without header
    """
    combined = username + ":" + password
    encoded = base64.b64encode(combined)
    return "basic {0}".format(encoded)


class DelayedMeter(object):
    """
    This class acts like a Meter but only calls the mark after a
    threshold has been hit or after a timed delay. The mark call is
    relatively expensive so we don't want to call it so often.
    """

    def __init__(self, meter, delayCount=10000):
        self._meter = meter
        self._delayCount = delayCount
        self._count = 0
        self._pushThread = None

    def mark(self, value=1):
        self._count += value
        if self._pushThread is None:
            self._pushThread = eventlet.spawn_after(10, self._pushMark)
        if self._count >= self._delayCount:
            self._pushMark()

    def _pushMark(self):
        self._meter.mark(self._count)
        self._count = 0
        if self._pushThread:
            self._pushThread.cancel()
            self._pushThread = None


NON_NUMERIC_CHARS = "".join(
    set(string.punctuation + string.ascii_letters)
    - set([".", "-", "+", "e", "E"])
)


def sanitized_float(unsanitized):
    """Return a float given an unsantized input.

    Behaves exactly like float() with the following differences:

    # Stripping of non-numeric characters.
    >>> sanitized_float('99.9%')
    99.9
    >>> sanitized_float('123 V')
    123.0
    >>> sanitized_float('not-applicable') is None
    True

    """
    try:
        if isinstance(unsanitized, float):
            return unsanitized

        if isinstance(unsanitized, (int, long)):
            return float(unsanitized)

        if isinstance(unsanitized, str):
            return float(unsanitized.translate(None, NON_NUMERIC_CHARS))

        if isinstance(unsanitized, unicode):
            return float(str(unsanitized).translate(None, NON_NUMERIC_CHARS))

    except Exception:
        log.warn("failed converting %r to float", unsanitized)
