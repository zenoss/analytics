##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import


class Hash(object):
    """A key/value store for hash data, e.g. nested key/value data."""

    def __init__(self, scan_page_size=1000):
        self.__scan_count = scan_page_size

    def exists(self, client, key, field=None):
        """
        If `fields` is given, returns True if the named field is present
        in the key.  If `fields` is None, returns True if the key exists.

        @type client: RedisClient
        @type field: str | None
        @type atoms: Map[str, str]
        @rtype: Boolean
        """
        if field:
            return client.hexists(key, field)
        return bool(client.exists(key))

    def scan(self, client, pattern):
        """
        Returns an iterable producing tuples containing the atoms of
        keys matching `atoms`.
        """
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (key for key in result)

    def get(self, client, key):
        """
        Returns the mapping stored in the key specified by `atoms`.
        """
        result = client.hgetall(key)
        return result if result else None

    def getfield(self, client, key, field):
        """
        Returns the value of the `field` store in the key given by `atoms`.
        """
        return client.hget(key, field)

    def set(self, client, key, mapping):
        """
        Use `mapping` to set or replace fields found in the key.

        @type mapping: Mapping[str, Union[bytes, str, int, float]]
        """
        client.hset(key, mapping=mapping)

    def delete(self, client, key):
        client.delete(key)

    def deletefields(self, client, key, *fields):
        """
        Delete the specified field from the key.
        """
        client.hdel(key, *fields)
