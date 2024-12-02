##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class _StringTable(object):
    """ """

    def __init__(self, template, scan_page_size=1000):
        self.__template = template
        self.__scan_count = 1000

    def make_key(self, **parts):
        return self.__template.format(**parts)

    def exists(self, client, **parts):
        return client.exists(self.make_key(**parts))

    def scan(self, client, **parts):
        pattern = self.make_key(**parts)
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (tuple(key.rsplit(":", len(parts))[1:]) for key in result)

    def get(self, client, **parts):
        key = self.make_key(**parts)
        return client.get(key)

    def set(self, client, data, **parts):
        key = self.make_key(**parts)
        client.set(key, data)

    def delete(self, client, **parts):
        key = self.make_key(**parts)
        client.delete(key)


class OidMapConfigTable(_StringTable):
    """
    Manages OidMap data.
    """

    def __init__(self, app, scan_page_size=1000):
        super(OidMapConfigTable, self).__init__(
            "{app}:oidmap:config:{{service}}:{{monitor}}".format(app=app),
            scan_page_size=scan_page_size
        )


class DeviceConfigTable(_StringTable):
    """
    Manages device configuration data for a specific configuration service.
    """

    def __init__(self, app, scan_page_size=1000):
        """Initialize a DeviceConfigTable instance."""
        super(DeviceConfigTable, self).__init__(
            "{app}:device:config:{{service}}:{{monitor}}:{{device}}".format(
                app=app
            ),
            scan_page_size=scan_page_size
        )
