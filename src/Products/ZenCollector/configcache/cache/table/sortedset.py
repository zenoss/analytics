##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import


class SortedSet(object):
    """
    Manages data stored as sorted sets.

    For each key, multiple values can be stored, each with its own score.
    The score determines the sort order of the values in the key.
    """

    def __init__(self, scan_page_size=1000):
        self.__scan_count = scan_page_size

    def scan(self, client, pattern):
        """
        Return an iterator of tuples of (key, value, score).

        @type client: redis client
        @type pattern: str
        @rtype Iterator[Tuple]
        """
        return (
            (key, value, score)
            for key in self._keys(client, pattern)
            for value, score in client.zscan_iter(key, count=self.__scan_count)
        )

    def range(self, client, pattern, maxscore=None, minscore=None):
        """
        Return an iterable of tuples of (key, value, score).

        @type client: redis client
        @type pattern: str
        @type minscore: Union[float, None]
        @type maxscore: Union[float, None]
        @rtype Iterator[Tuple[*str, float]]
        """
        maxv = maxscore if maxscore is not None else "+inf"
        minv = minscore if minscore is not None else "-inf"
        return (
            (key, value, score)
            for key in self._keys(client, pattern)
            for value, score in client.zrangebyscore(
                key, minv, maxv, withscores=True
            )
        )

    def exists(self, client, key, value):
        """
        Return True if a score for `value` exists in `key`.

        @type client: RedisClient
        @type key: str
        @type value: str
        @rtype: Boolean
        """
        return client.zscore(key, value) is not None

    def add(self, client, key, value, score):
        """
        Sets a `score` for the `value` in `key`.

        @type client: RedisClient
        @type key: str
        @type value: str
        @type score: float
        """
        client.zadd(key, {value: score})

    def score(self, client, key, value):
        """
        Returns the score associated with `value` from `key`.
        Returns None if no score is found.

        @type client: RedisClient
        @type key: str
        @type value: str
        """
        return client.zscore(key, value)

    def delete(self, client, key, value):
        """
        Removes a `value` from `key`.
        """
        client.zrem(key, value)

    def _keys(self, client, pattern):
        return (
            key
            for key in client.scan_iter(match=pattern, count=self.__scan_count)
        )
