##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class DeviceUIDTable(object):
    """
    Manages mapping device names to their ZODB UID.
    """

    def __init__(self, app, scan_page_size=1000, mget_page_size=10):
        """Initialize a DeviceUIDTable instance."""
        self.__template = "{app}:device:uid:{{device}}".format(app=app)
        self.__scan_count = scan_page_size
        self.__mget_count = mget_page_size

    def make_key(self, device):
        return self.__template.format(device=device)

    def exists(self, client, device):
        """Return True if configuration data exists for the given ID.

        :param device: The ID of the device
        :type device: str
        :rtype: boolean
        """
        return client.exists(self.make_key(device))

    def scan(self, client, device="*"):
        """
        Return an iterable of tuples of device names.
        """
        pattern = self.make_key(device)
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (key.rsplit(":", 1)[-1] for key in result)

    def get(self, client, device):
        """Return the UID of the given device name.

        :type device: str
        :rtype: str
        """
        key = self.make_key(device)
        return client.get(key)

    def set(self, client, device, uid):
        """Insert or replace the UID for the given device.

        :param device: The ID of the configuration
        :type device: str
        :param uid: The ZODB UID of the device
        :type uid: str
        :raises: ValueError
        """
        key = self.make_key(device)
        client.set(key, uid)

    def delete(self, client, *devices):
        """Delete one or more keys.

        This method does not fail if the key doesn't exist.

        :type uids: Sequence[str]
        """
        keys = tuple(self.make_key(dvc) for dvc in devices)
        client.delete(*keys)
