##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from ..utils import batched


class String(object):
    """A key/value store for string data."""

    def __init__(self, scan_page_size=1000, mget_page_size=100):
        self.__scan_count = scan_page_size
        self.__mget_page = mget_page_size

    def exists(self, client, key):
        """
        Returns True if the `key` is present in Redis.

        @rtype: boolean
        """
        return bool(client.exists(key))

    def scan(self, client, pattern):
        """
        Returns an iterator producing keys that match `pattern`.

        @type pattern: str
        @rtype: Iterator[str]
        """
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (key for key in result)

    def mget(self, client, *keys):
        """
        Returns an iterator producing key/value pairs for each key in `keys`.

        @type keys: Sequence[str]
        @rtype: Iterator[Tuple[str, str | None]]
        """
        return (
            (key, value)
            for batch in batched(keys, self.__mget_page)
            for key, value in zip(batch, client.mget(*batch))
        )

    def get(self, client, key):
        """
        Returns the value corresponding to `key`.
        Returns None if `key` is not found.

        @type key: str
        @rtype: str | None
        """
        return client.get(key)

    def set(self, client, key, value):
        """
        Sets the `value` for `key`.

        @type key: str
        @type value: str | int | float
        @rtype: str | None
        """
        client.set(key, value)

    def delete(self, client, key):
        """
        Removes the value associated with `key`.

        @type key: str
        """
        client.delete(key)
