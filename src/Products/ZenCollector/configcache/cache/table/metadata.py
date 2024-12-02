##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class ConfigMetadataTable(object):
    """
    Manages the mapping of device configurations to monitors.

    Configuration IDs are mapped to service ID/monitor ID pairs.

    A Service ID/monitor ID pair are used as a key to retrieve the
    Configuration IDs mapped to the pair.
    """

    def __init__(self, app, category):
        """Initialize a ConfigMetadataStore instance."""
        self.__template = (
            "{app}:device:{category}:{{service}}:{{monitor}}".format(
                app=app, category=category
            )
        )
        self.__scan_count = 1000

    def make_key(self, service, monitor):
        return self.__template.format(service=service, monitor=monitor)

    def get_pairs(self, client, service="*", monitor="*"):
        pattern = self.make_key(service, monitor)
        return (
            key.rsplit(":", 2)[1:]
            for key in client.scan_iter(match=pattern, count=self.__scan_count)
        )

    def scan(self, client, pairs):
        """
        Return an iterable of tuples of (service, monitor, device, score).

        @type client: redis client
        @type pairs: Iterable[Tuple[str, str]]
        @rtype Iterator[Tuple[str, str, str, float]]
        """
        return (
            (service, monitor, dvc, score)
            for service, monitor in pairs
            for dvc, score in client.zscan_iter(
                self.make_key(service, monitor), count=self.__scan_count
            )
        )

    def range(self, client, pairs, maxscore=None, minscore=None):
        """
        Return an iterable of tuples of (service, monitor, device, score).

        @type client: redis client
        @type pairs: Iterable[Tuple[str, str]]
        @type minscore: Union[float, None]
        @type maxscore: Union[float, None]
        @rtype Iterator[Tuple[str, str, str, float]]
        """
        maxv = maxscore if maxscore is not None else "+inf"
        minv = minscore if minscore is not None else "-inf"
        return (
            (service, monitor, device, score)
            for service, monitor in pairs
            for device, score in client.zrangebyscore(
                self.make_key(service, monitor), minv, maxv, withscores=True
            )
        )

    def exists(self, client, service, monitor, device):
        """Return True if a score for the key and device exists.

        @type client: RedisClient
        @type service: str
        @type monitor: str
        @type device: str
        """
        key = self.make_key(service, monitor)
        return client.zscore(key, device) is not None

    def add(self, client, service, monitor, device, score):
        """
        Add a (device, score) -> (monitor, serviceid) mapping.
        This method will replace any existing mapping for device.

        @type client: RedisClient
        @type service: str
        @type monitor: str
        @type device: str
        @type score: float
        """
        key = self.make_key(service, monitor)
        client.zadd(key, {device: score})

    def score(self, client, service, monitor, device):
        """
        Returns the timestamp associated with the device ID.
        Returns None of the device ID is not found.
        """
        key = self.make_key(service, monitor)
        return client.zscore(key, device)

    def delete(self, client, service, monitor, device):
        """
        Removes a device from a (service, monitor) key.
        """
        key = self.make_key(service, monitor)
        client.zrem(key, device)
