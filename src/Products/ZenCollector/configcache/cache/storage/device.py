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
# configcache:device:uid:<device> <uid>
# configcache:device:config:<service>:<monitor>:<device> <config>
# configcache:device:age:<service>:<monitor> [(<score>, <device>), ...]
# configcache:device:retired:<service>:<monitor> [(<score>, <device>), ...]
# configcache:device:expired:<service>:<monitor> [(<score>, <device>), ...]
# configcache:device:pending:<service>:<monitor> [(<score>, <device>), ...]
# configcache:device:building:<service>:<monitor> [(<score>, <device>), ...]
#
# While "device" seems redundant, other values in this position could be
# "threshold" and "property".
#
# * uid - Maps a device to its object path in ZODB
# * config - Maps a key (<service>:<monitor>:<device>) to a configuration
# * age - Stores the timestamp for when the configuration was created
#
# The following keys store the state of a device's config.
#
# * retired - devices with a 'retired' config.
#
#      The <score> is a copy from the 'age' key.  Since retirement is
#      controlled by a z-property, storing the time when the config
#      transitioned to 'retire' is not useful because the z-property
#      can change dynamically.
#
# * expired - devices with an 'expired' config.
#
#      The <score> is the timestamp when the config was expired.
#
# * pending - devices with a 'pending' config
#
#      The <score> is the timestamp when the build_device_config job
#      was submitted.
#
# * building - devices with a 'building' config
#
#      The <score> is the timestamp when the build_device_config job
#      began execution.
#
# A device may exist in only one of 'retired', 'expired', 'pending',
# 'building', or none of them.
#
# <service> names the configuration service class used to generate the
# configuration.
# <monitor> names the monitor (collector) the device belongs to.
# <device> is the ID of the device
# <uid> is the object path to the device in ZODB.
#

from __future__ import absolute_import, print_function, division

import inspect
import json
import logging
import re
import types
import zlib

from functools import partial
from itertools import chain

import attr
import six

from attr.validators import instance_of
from twisted.spread.jelly import jelly, unjelly
from zope.component.factory import Factory

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..model import (
    DeviceKey,
    DeviceQuery,
    DeviceRecord,
    ConfigStatus,
    KeyConverter,
)
from ..table import String, SortedSet

_app = "configcache"
log = logging.getLogger("zen.configcache.storage")


class DeviceConfigStoreFactory(Factory):
    """
    IFactory implementation for ConfigStore objects.
    """

    def __init__(self):
        super(DeviceConfigStoreFactory, self).__init__(
            DeviceConfigStore,
            "DeviceConfigStore",
            "Device Configuration Cache Storage",
        )


_uid_template = "{app}:device:uid:{{device}}"
_config_template = "{app}:device:config:{{service}}:{{monitor}}:{{device}}"
_status_template = "{app}:device:{category}:{{service}}:{{monitor}}"


class DeviceConfigStore(object):
    """
    A device config store.
    """

    @classmethod
    def make(cls):
        """Create and return a ConfigStore object."""
        client = getRedisClient(url=getRedisUrl())
        return cls(client)

    def __init__(self, client):
        """Initialize a ConfigStore instance."""
        self.__client = client
        self.__uids = _StringTable(
            _uid_template.format(app=_app), keytype=_UIDKey
        )
        self.__config = _StringTable(_config_template.format(app=_app))
        self.__age = _SortedSetTable(
            _status_template.format(app=_app, category="age")
        )
        self.__retired = _SortedSetTable(
            _status_template.format(app=_app, category="retired")
        )
        self.__expired = _SortedSetTable(
            _status_template.format(app=_app, category="expired")
        )
        self.__pending = _SortedSetTable(
            _status_template.format(app=_app, category="pending")
        )
        self.__building = _SortedSetTable(
            _status_template.format(app=_app, category="building")
        )
        self.__range = type(
            "rangefuncs",
            (object,),
            {
                "age": partial(_range, self.__client, self.__age),
                "retired": partial(_range, self.__client, self.__retired),
                "expired": partial(_range, self.__client, self.__expired),
                "pending": partial(_range, self.__client, self.__pending),
                "building": partial(_range, self.__client, self.__building),
            },
        )()

    def __contains__(self, key):
        """
        Returns True if a config for the given key exists.

        @type key: DeviceKey
        @rtype: Boolean
        """
        return self.__config.exists(self.__client, key)

    def __iter__(self):
        """
        Returns an iterable producing the keys for all existing configs.

        @rtype: Iterator[DeviceKey]
        """
        return iter(
            DeviceKey(**self.__config.parse_rawkey(raw))
            for raw in self.__config.scan(self.__client, DeviceQuery())
        )

    def search(self, query=None):
        """
        Returns the configuration keys matching the search criteria.

        @type query: DeviceQuery
        @rtype: Iterator[DeviceKey]
        @raises TypeError: Unsupported value given for a field
        @raises AttributeError: Unknown field
        """
        if query is None:
            query = DeviceQuery()
        if not isinstance(query, DeviceQuery):
            raise TypeError("'{!r} is not a DeviceQuery".format(query))
        return self._query(**attr.asdict(query))

    def add(self, record):
        """
        @type record: DeviceRecord
        """
        self._add(record, self._delete_statuses)

    def put_config(self, record):
        """
        Updates the config without changing its status.

        @type record: DeviceRecord
        """
        self._add(record)

    def _add(self, record, statushandler=lambda *args: None):
        svc, mon, dvc, uid, updated, config = _from_record(record)
        orphaned_keys = tuple(
            key
            for key in self._query(service=svc, device=dvc)
            if key.monitor != mon
        )
        watch_keys = self._get_watch_keys(orphaned_keys + (record.key,))
        stored_uid = self.__uids.get(self.__client, _UIDKey(dvc))

        def _add_impl(pipe):
            pipe.multi()
            # Remove configs for this device that exist with a different
            # monitor.
            # Note: configs produced by different configuration services
            # may exist simultaneously.
            for key in orphaned_keys:
                self.__config.delete(pipe, key)
                self.__age.delete(pipe, key, key.device)
                self._delete_statuses(pipe, key)
            if stored_uid != uid:
                self.__uids.set(pipe, _UIDKey(record.key.device), uid)
            self.__config.set(pipe, record.key, config)
            self.__age.add(pipe, record.key, dvc, updated)
            statushandler(pipe, record.key)

        self.__client.transaction(_add_impl, *watch_keys)

    def get_uid(self, deviceId):
        """
        Return the ZODB UID (path) for the given device.

        @type deviceId: str
        @rtype: str | None
        """
        return self.__uids.get(self.__client, _UIDKey(deviceId))

    def get_uids(self, *deviceids):
        """
        Return the ZODB UID (path) for each of the given devices.

        The return value is an iterator producing two element tuples:

            (<device>, <uid or None>)

        The second element of the tuple has the value None if no UID
        exists for the requested device.

        @type deviceids: List[str]
        @rtype: Iterator[Tuple[str, str|None]]
        """
        keys = tuple(_UIDKey(dvc) for dvc in deviceids)
        return (
            (self.__uids.parse_rawkey(raw)["device"], uid)
            for raw, uid in self.__uids.mget(self.__client, *keys)
        )

    def get_updated(self, key):
        """
        Return the timestamp of when the config was built.

        @type key: DeviceKey
        @rtype: float
        """
        return _to_ts(self.__age.score(self.__client, key, key.device))

    def query_updated(self, query=None):
        """
        Return the last update timestamp of every configuration selected
        by the query.

        @type query: DeviceQuery
        @rtype: Iterable[Tuple[DeviceKey, float]]
        """
        if query is None:
            query = DeviceQuery()
        predicate = self._get_device_predicate(query.device)
        return (
            (key, ts)
            for key, ts in self._get_metadata(self.__age, query)
            if predicate(key.device)
        )

    def get(self, key, default=None):
        """
        @type key: DeviceKey
        @rtype: DeviceRecord
        """
        with self.__client.pipeline() as pipe:
            self.__config.get(pipe, key)
            self.__age.score(pipe, key, key.device)
            self.__uids.get(pipe, _UIDKey(key.device))
            conf, score, uid = pipe.execute()
        if conf is None:
            return default
        score = 0 if score < 0 else score
        return _to_record(
            key.service, key.monitor, key.device, uid, score, conf
        )

    def remove(self, *keys):
        """
        Delete the configurations identified by `keys`.

        @type keys: Sequence[DeviceKey]
        """
        with self.__client.pipeline() as pipe:
            for key in keys:
                self.__config.delete(pipe, key)
                self.__age.delete(pipe, key, key.device)
                self._delete_statuses(pipe, key)
            pipe.execute()

        given = {key.device for key in keys}
        remaining = {
            key.device
            for key in chain.from_iterable(
                self._query(device=device) for device in given
            )
        }
        deleted = given - remaining
        if deleted:
            with self.__client.pipeline() as pipe:
                for device in deleted:
                    self.__uids.delete(pipe, _UIDKey(device))
                pipe.execute()

    def _query(self, service="*", monitor="*", device="*"):
        return (
            DeviceKey(**self.__config.parse_rawkey(raw))
            for raw in self.__config.scan(
                self.__client,
                DeviceQuery(service=service, monitor=monitor, device=device),
            )
        )

    def clear_status(self, *keys):
        """
        Removes retired, expired, pending, and building statuses.

        If a config is present, the status becomes current.  If no config
        is present, then there is no status.

        @type keys: Sequence[DeviceKey]
        """
        if len(keys) == 0:
            return

        def clear_impl(pipe):
            pipe.multi()
            for key in keys:
                self._delete_statuses(pipe, key)

        watch_keys = self._get_watch_keys(keys)
        self.__client.transaction(clear_impl, *watch_keys)

    def _delete_statuses(self, pipe, key):
        self.__retired.delete(pipe, key, key.device)
        self.__expired.delete(pipe, key, key.device)
        self.__pending.delete(pipe, key, key.device)
        self.__building.delete(pipe, key, key.device)

    def set_retired(self, *pairs):
        """
        Marks the indicated configuration(s) as retired.

        @type keys: Sequence[(DeviceKey, float)]
        """

        def _impl(rows, pipe):
            pipe.multi()
            for key, ts in rows:
                score = _to_score(ts)
                self.__retired.add(pipe, key, key.device, score)
                self.__expired.delete(pipe, key, key.device)
                self.__pending.delete(pipe, key, key.device)
                self.__building.delete(pipe, key, key.device)

        self._set_status(pairs, _impl)

    def set_expired(self, *pairs):
        """
        Marks the indicated configuration(s) as expired.

        @type keys: Sequence[(DeviceKey, float)]
        """

        def _impl(rows, pipe):
            pipe.multi()
            for key, ts in rows:
                score = _to_score(ts)
                self.__retired.delete(pipe, key, key.device)
                self.__expired.add(pipe, key, key.device, score)
                self.__pending.delete(pipe, key, key.device)
                self.__building.delete(pipe, key, key.device)

        self._set_status(pairs, _impl)

    def set_pending(self, *pairs):
        """
        Marks configuration(s) as waiting for a new configuration.

        @type pending: Sequence[(DeviceKey, float)]
        """

        def _impl(rows, pipe):
            pipe.multi()
            for key, ts in rows:
                score = _to_score(ts)
                self.__retired.delete(pipe, key, key.device)
                self.__expired.delete(pipe, key, key.device)
                self.__pending.add(pipe, key, key.device, score)
                self.__building.delete(pipe, key, key.device)

        self._set_status(pairs, _impl)

    def set_building(self, *pairs):
        """
        Marks configuration(s) as building a new configuration.

        @type pairs: Sequence[(DeviceKey, float)]
        """

        def _impl(rows, pipe):
            pipe.multi()
            for key, ts in rows:
                score = _to_score(ts)
                self.__retired.delete(pipe, key, key.device)
                self.__expired.delete(pipe, key, key.device)
                self.__pending.delete(pipe, key, key.device)
                self.__building.add(pipe, key, key.device, score)

        self._set_status(pairs, _impl)

    def _set_status(self, pairs, fn):
        if len(pairs) == 0:
            return

        watch_keys = self._get_watch_keys(key for key, _ in pairs)
        # rows = tuple(
        #     (key.service, key.monitor, key.device, ts) for key, ts in pairs
        # )

        callback = partial(fn, pairs)
        self.__client.transaction(callback, *watch_keys)

    def _get_watch_keys(self, keys):
        return set(
            chain.from_iterable(
                (
                    self.__age.to_rawkey(key),
                    self.__retired.to_rawkey(key),
                    self.__expired.to_rawkey(key),
                    self.__pending.to_rawkey(key),
                    self.__building.to_rawkey(key),
                )
                for key in keys
            )
        )

    def get_status(self, key):
        """
        Returns the current status of the config identified by `key`.

        @type key: DeviceKey
        @rtype: ConfigStatus | None
        """
        scores = self._get_scores(key)
        if not any(scores):
            return None
        return self._get_status_from_scores(scores, key)

    def query_statuses(self, query=None):
        """
        Return all status objects matching the query.

        @type query: DeviceQuery
        @rtype: Iterable[ConfigStatus]
        """
        if query is None:
            query = DeviceQuery()
        keys = set()
        tables = (
            (self.__expired, ConfigStatus.Expired),
            (self.__retired, ConfigStatus.Retired),
            (self.__pending, ConfigStatus.Pending),
            (self.__building, ConfigStatus.Building),
        )
        predicate = self._get_device_predicate(query.device)

        for table, cls in tables:
            for key, ts in self._get_metadata(table, query):
                if predicate(key.device):
                    keys.add(key)
                    yield cls(key, ts)
        for key, ts in self._get_metadata(self.__age, query):
            # Skip age (aka 'current') data for keys that already have
            # some other status.
            if key in keys:
                continue
            if predicate(key.device):
                yield ConfigStatus.Current(key, ts)

    def _get_device_predicate(self, spec):
        if spec == "*":
            return lambda _: True
        elif "*" in spec:
            expr = spec.replace("*", ".*")
            regex = re.compile(expr)
            return lambda value: regex.match(value) is not None
        else:
            return lambda value: value == spec

    def _get_metadata(self, table, query):
        return (
            (
                DeviceKey(device=device, **table.parse_rawkey(raw)),
                _to_ts(score),
            )
            for raw, device, score in table.scan(self.__client, query)
        )

    def _get_status_from_scores(self, scores, key):
        age, retired, expired, pending, building = scores
        if building is not None:
            return ConfigStatus.Building(key, _to_ts(building))
        elif pending is not None:
            return ConfigStatus.Pending(key, _to_ts(pending))
        elif expired is not None:
            return ConfigStatus.Expired(key, _to_ts(expired))
        elif retired is not None:
            return ConfigStatus.Retired(key, _to_ts(retired))
        elif age is not None:
            return ConfigStatus.Current(key, _to_ts(age))

    def get_building(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Building objects.

        @rtype: Iterable[ConfigStatus.Building]
        """
        query = DeviceQuery(service=service, monitor=monitor)
        return (
            ConfigStatus.Building(key, ts)
            for key, ts in self.__range.building(query)
        )

    def get_pending(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Pending objects.

        @rtype: Iterable[ConfigStatus.Pending]
        """
        query = DeviceQuery(service=service, monitor=monitor)
        return (
            ConfigStatus.Pending(key, ts)
            for key, ts in self.__range.pending(query)
        )

    def get_expired(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Expired objects.

        @rtype: Iterable[ConfigStatus.Expired]
        """
        query = DeviceQuery(service=service, monitor=monitor)
        return (
            ConfigStatus.Expired(key, ts)
            for key, ts in self.__range.expired(query)
        )

    def get_retired(self, service="*", monitor="*"):
        """
        Return an iterator producing ConfigStatus.Retired objects.

        @rtype: Iterable[ConfigStatus.Retired]
        """
        query = DeviceQuery(service=service, monitor=monitor)
        return (
            ConfigStatus.Retired(key, ts)
            for key, ts in self.__range.retired(query)
        )

    def get_older(self, maxtimestamp, service="*", monitor="*"):
        """
        Returns an iterator producing ConfigStatus.Current objects
        where current timestamp <= `maxtimestamp`.

        @rtype: Iterable[ConfigStatus.Current]
        """
        query = DeviceQuery(service=service, monitor=monitor)
        # NOTE: 'older' means timestamps > 0 and <= `maxtimestamp`.
        selection = tuple(
            (key, age)
            for key, age in self.__range.age(
                query, minv="(0", maxv=_to_score(maxtimestamp)
            )
        )
        for key, age in selection:
            scores = self._get_scores(key)[1:]
            if any(score is not None for score in scores):
                continue
            yield ConfigStatus.Current(key, age)

    def get_newer(self, mintimestamp, service="*", monitor="*"):
        """
        Returns an iterator producing ConfigStatus.Current objects
        where current timestamp > `mintimestamp`.

        @rtype: Iterable[ConfigStatus.Current]
        """
        query = DeviceQuery(service=service, monitor=monitor)
        # NOTE: 'newer' means timestamps  to `maxtimestamp`.
        selection = tuple(
            (key, age)
            for key, age in self.__range.age(
                query, minv="(%s" % (_to_score(mintimestamp),)
            )
        )
        for key, age in selection:
            scores = self._get_scores(key)[1:]
            if any(score is not None for score in scores):
                continue
            yield ConfigStatus.Current(key, age)

    def _get_scores(self, key):
        service, monitor, device = attr.astuple(key)
        with self.__client.pipeline() as pipe:
            self.__age.score(pipe, key, key.device)
            self.__retired.score(pipe, key, key.device)
            self.__expired.score(pipe, key, key.device)
            self.__pending.score(pipe, key, key.device)
            self.__building.score(pipe, key, key.device)
            return pipe.execute()


def _range(client, table, query, minv=None, maxv=None):
    pattern = table.to_rawkey(query)
    return (
        (DeviceKey(device=device, **table.parse_rawkey(raw)), _to_ts(score))
        for raw, device, score in table.range(
            client, pattern, minscore=minv, maxscore=maxv
        )
    )


def _deserialize(data):
    # Python2's `unicode` built-in won't accept a unicode string when the
    # `encoding` parameter is given.  Twisted's `unjelly` function assumes
    # that a Unicode value is an utf-8-encoded non-unicode string.  However,
    # by default, all strings from a JSON loader are Unicode strings, so
    # Twisted's `unjelly` function fails on the unicode value.
    #
    # The fix is add a hook to ensure that all strings are converted into
    # binary (non-unicode) strings.  However, Twisted's jelly format is
    # s-expressions, which are basically nested lists, and there's no JSON
    # hook for lists.  So, wrap the data into a JSON-object (a dict) and
    # use a function to customize the decoding.
    try:
        data = zlib.decompress(data)
    except zlib.error:
        pass
    data = '{{"config":{}}}'.format(data)
    return unjelly(json.loads(data, object_hook=_decode_config))


def _decode_config(data):
    return _decode_list(data.get("config"))


def _decode_list(data):
    return [_decode_item(item) for item in data]


def _decode_item(item):
    if isinstance(item, six.text_type):
        return item.encode("utf-8")
    elif isinstance(item, list):
        return _decode_list(item)
    else:
        return item


def _serialize(config):
    return zlib.compress(json.dumps(jelly(config)))


def _to_score(ts):
    return ts * 1000.0


def _to_ts(score):
    return score / 1000.0


def _to_record(svc, mon, dvc, uid, updated, config):
    key = DeviceKey(svc, mon, dvc)
    updated = _to_ts(updated)
    config = _deserialize(config)
    return DeviceRecord(key, uid, updated, config)


def _from_record(record):
    return (
        record.service,
        record.monitor,
        record.device,
        record.uid,
        _to_score(record.updated),
        _serialize(record.config),
    )


@attr.s(frozen=True, slots=True)
class _UIDKey(object):
    device = attr.ib(converter=str, validator=instance_of(str))


class _CompositeTable(object):
    """
    Composite of a table type and KeyManager.
    """

    def __init__(self, template, tabletype, keytype, querytype):
        self.__km = KeyConverter(
            template, keytype=keytype, querytype=querytype
        )
        self.__table = tabletype()
        self.__methods = {
            t[0]: t[1]
            for t in inspect.getmembers(self.__table)
            if not t[0].startswith("_") and isinstance(t[1], types.MethodType)
        }

    @property
    def keys(self):
        return self.__km

    def mget(self, client, *keys):
        # The mget method accepts multiple keys and so must be handled
        # differently than _callmethod, which accepts only one key.
        rawkeys = tuple(self.__km.to_raw(k) for k in keys)
        return self.__methods["mget"](client, *rawkeys)

    def to_rawkey(self, key):
        return self.__km.to_raw(key)

    def parse_rawkey(self, raw):
        return self.__km.parse(raw)

    def __getattr__(self, name):
        method = self.__methods.get(name)
        if method is None:
            raise AttributeError("Attribute not found '{}'".format(name))
        return partial(self._callmethod, method)

    def _callmethod(self, method, client, key, *args, **kw):
        rawkey = self.__km.to_raw(key)
        return method(client, rawkey, *args, **kw)


class _SortedSetTable(_CompositeTable):
    def __init__(self, template):
        super(_SortedSetTable, self).__init__(
            template, SortedSet, DeviceKey, DeviceQuery
        )


class _StringTable(_CompositeTable):
    def __init__(self, template, keytype=DeviceKey):
        super(_StringTable, self).__init__(
            template, String, keytype, DeviceQuery
        )
