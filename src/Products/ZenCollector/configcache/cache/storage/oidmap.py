##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Key structure
# =============
# configcache:oidmap:config <config>
# configcache:oidmap:state {
#     "checksum": ...,
#     "created": ...,
#     "status": ...,
#     "effective": ...
# }
#
# * config - the oid map.
# * hash - the hash of the current oid map
# * created - timestamp of when the oid map was created
# * status - identifies the oid map's status (expired, pending, building)
# * effective - timestamp of when the status took effect
#
# No value for "status" means the status of the oidmap is Current.
#
# "status" is "expired", "pending", or "building"
#

from __future__ import absolute_import, print_function, division

import ast
import json
import logging
import zlib

from twisted.spread.jelly import jelly, unjelly
from zope.component.factory import Factory

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..model import CacheKey, ConfigStatus, OidMapRecord
from ..table import Hash, String

_app = "configcache"
log = logging.getLogger("zen.configcache.storage.oidmap")


class OidMapStoreFactory(Factory):
    """
    IFactory implementation for OidMapStore objects.
    """

    def __init__(self):
        super(OidMapStoreFactory, self).__init__(
            OidMapStore,
            "OidMapStore",
            "OID Map Cache Storage",
        )


_template_oidmap = "{app}:oidmap:config"
_template_state = "{app}:oidmap:state"

_status_map = {
    cls.__name__: cls
    for cls in (
        ConfigStatus.Expired,
        ConfigStatus.Pending,
        ConfigStatus.Building,
    )
}


class _FieldNames(object):
    checksum = "checksum"
    created = "created"
    status = "status"
    effective = "effective"


class OidMapStore(object):
    """
    An OID map store.
    """

    @classmethod
    def make(cls):
        """Create and return a OidMapStore object."""
        client = getRedisClient(url=getRedisUrl())
        return cls(client)

    def __init__(self, client):
        """Initialize a OidMapStore instance."""
        self.__client = client
        self.__oidmap_key = _template_oidmap.format(app=_app)
        self.__oids = String()
        self.__state_key = _template_state.format(app=_app)
        self.__state = Hash()

    def __nonzero__(self):
        return self.__client.exists(self.__oidmap_key)

    def remove(self):
        with self.__client.pipeline() as pipe:
            self.__oids.delete(pipe, self.__oidmap_key)
            self.__state.delete(pipe, self.__state_key)
            pipe.execute()

    def get_checksum(self):
        return self.__state.getfield(
            self.__client, self.__state_key, _FieldNames.checksum
        )

    def get_created(self):
        created = self.__state.getfield(
            self.__client, self.__state_key, _FieldNames.created
        )
        if created is not None:
            created = float(created)
        return created

    def get_status(self):
        state = self.__state.get(self.__client, self.__state_key)
        if not state:
            return None
        status_name = state.get(_FieldNames.status)
        if status_name is None:
            return ConfigStatus.Current(
                CacheKey(), float(state[_FieldNames.created])
            )
        status_cls = _status_map.get(status_name)
        if status_cls is None:
            raise RuntimeError(
                "invalid status for oidmap: {}".format(status_name)
            )
        return status_cls(CacheKey(), float(state[_FieldNames.effective]))

    def get(self, default=None):
        with self.__client.pipeline() as pipe:
            self.__oids.get(pipe, self.__oidmap_key)
            self.__state.get(pipe, self.__state_key)
            oids, state = pipe.execute()
        if oids is None:
            return default
        return _to_record(
            state.get(_FieldNames.created),
            state.get(_FieldNames.checksum),
            oids,
        )

    def add(self, record):
        """
        Adds or updates the OidMap and changes the status to Current.

        @type record: OidMapRecord
        """
        self._add(record, self._delete_status)

    def put(self, record):
        """
        Updates the OidMap without changing its status.

        @type record: OidMapRecord
        """
        self._add(record)

    def _add(self, record, statushandler=lambda *args, **kw: None):
        created, checksum, oidmap = _from_record(record)
        watch_keys = (self.__oidmap_key, self.__state_key)

        def _add_impl(pipe):
            pipe.multi()
            self.__oids.set(pipe, self.__oidmap_key, oidmap)
            self.__state.set(
                pipe,
                self.__state_key,
                {_FieldNames.checksum: checksum, _FieldNames.created: created},
            )
            statushandler(pipe)

        self.__client.transaction(_add_impl, *watch_keys)

    def _delete_status(self, client):
        self.__state.deletefields(
            client, self.__state_key, _FieldNames.status, _FieldNames.effective
        )

    def set_expired(self, timestamp):
        """
        Marks the indicated oidmap(s) as expired.

        @type timestamp: float
        """
        self._set_status(timestamp, ConfigStatus.Expired.__name__)

    def set_pending(self, timestamp):
        """
        Marks configuration(s) as waiting for a new configuration.

        @type pending: Sequence[(OidMapKey, float)]
        """
        self._set_status(timestamp, ConfigStatus.Pending.__name__)

    def set_building(self, timestamp):
        """
        Marks configuration(s) as building a new configuration.

        @type pairs: Sequence[(OidMapKey, float)]
        """
        self._set_status(timestamp, ConfigStatus.Building.__name__)

    def _set_status(self, timestamp, status_name):
        watch_keys = (self.__state_key,)

        def _impl(pipe):
            pipe.multi()
            self.__state.set(
                pipe,
                self.__state_key,
                {
                    _FieldNames.status: status_name,
                    _FieldNames.effective: timestamp,
                },
            )

        self.__client.transaction(_impl, *watch_keys)


def _deserialize(data):
    return unjelly(ast.literal_eval(zlib.decompress(data)))


def _serialize(oidmap):
    return zlib.compress(json.dumps(jelly(oidmap)))


def _to_record(created, checksum, oidmap):
    created = float(created)
    oidmap = _deserialize(oidmap)
    return OidMapRecord(created, checksum, oidmap)


def _from_record(record):
    return (
        record.created,
        record.checksum,
        _serialize(record.oidmap),
    )
