##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections

import attr

from attr.validators import instance_of

from Products.ZenCollector.services.config import DeviceProxy

from .utils import parse_atoms, extract_atoms


__all__ = (
    "DeviceKey",
    "DeviceQuery",
    "DeviceRecord",
    "ConfigStatus",
    "OidMapRecord",
    "KeyConverter",
)


@attr.s(frozen=True, slots=True)
class CacheKey(object):
    """
    Stub key class for tables that have a fixed (no parameters) key.
    """


@attr.s(slots=True)
class OidMapRecord(object):
    created = attr.ib(validator=instance_of(float))
    checksum = attr.ib(validator=instance_of(str))
    oidmap = attr.ib(validator=instance_of(dict))

    @classmethod
    def make(cls, created, checksum, oidmap):
        return cls(created=created, checksum=checksum, oidmap=oidmap)


@attr.s(frozen=True, slots=True)
class DeviceQuery(object):
    service = attr.ib(converter=str, validator=instance_of(str), default="*")
    monitor = attr.ib(converter=str, validator=instance_of(str), default="*")
    device = attr.ib(converter=str, validator=instance_of(str), default="*")


@attr.s(frozen=True, slots=True)
class DeviceKey(CacheKey):
    service = attr.ib(converter=str, validator=instance_of(str))
    monitor = attr.ib(converter=str, validator=instance_of(str))
    device = attr.ib(converter=str, validator=instance_of(str))


@attr.s(slots=True)
class DeviceRecord(object):
    key = attr.ib(
        validator=instance_of(DeviceKey), on_setattr=attr.setters.NO_OP
    )
    uid = attr.ib(validator=instance_of(str), on_setattr=attr.setters.NO_OP)
    updated = attr.ib(validator=instance_of(float))
    config = attr.ib(validator=instance_of(DeviceProxy))

    @classmethod
    def make(cls, svc, mon, dev, uid, updated, config):
        return cls(DeviceKey(svc, mon, dev), uid, updated, config)

    @property
    def service(self):
        return self.key.service

    @property
    def monitor(self):
        return self.key.monitor

    @property
    def device(self):
        return self.key.device


@attr.s(slots=True)
class _Status(object):
    """Base class for status classes."""

    key = attr.ib(validator=instance_of(CacheKey))


class _ConfigStatus(object):
    """
    Namespace class for Current, Retired, Expired, Pending, and Building types.
    """

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Current(_Status):
        """The configuration is current."""

        updated = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Retired(_Status):
        """The cofiguration is retired, but not yet expired."""

        retired = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Expired(_Status):
        """The configuration has expired."""

        expired = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Pending(_Status):
        """The configuration is waiting for a rebuild."""

        submitted = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Building(_Status):
        """The configuration is rebuilding."""

        started = attr.ib(validator=instance_of(float))

    def __contains__(self, value):
        return isinstance(
            value,
            (
                _ConfigStatus.Current,
                _ConfigStatus.Retired,
                _ConfigStatus.Expired,
                _ConfigStatus.Pending,
                _ConfigStatus.Building,
            ),
        )


ConfigStatus = _ConfigStatus()


class KeyConverter(object):
    def __init__(self, template, keytype=CacheKey, querytype=None):
        self.__template = template
        self.__keytype = keytype
        self.__querytype = querytype
        self.__cache = _Cache()
        self.__atoms = parse_atoms(template)
        self.__atom_cnt = len(self.__atoms)

    def _atoms(self, raw):
        extracted = extract_atoms(raw, ":", self.__atom_cnt)
        return dict(zip(self.__atoms, extracted))

    def to_raw(self, key):
        """
        Return an encoded raw key using the content of `key`.
        """
        if not isinstance(key, (self.__keytype, self.__querytype)):
            return key
        hkey = _hashkey(key)
        value = self.__cache.get(hkey)
        if value is None:
            value = self.__template.format(**attr.asdict(key))
            self.__cache[hkey] = value
        return value

    def from_raw(self, raw):
        """
        Return an instance of keytype using the contents of `raw`.
        """
        hkey = _hashkey(raw)
        value = self.__cache.get(hkey)
        if value is None:
            value = self.__keytype(**self._atoms(raw))
            self.__cache[hkey] = value
        return value

    def parse(self, raw):
        """
        Return a dict containing the parsed components from the raw key.
        """
        return self._atoms(raw)


class _HashedTuple(tuple):
    __hashvalue = None

    def __hash__(self, hash=tuple.__hash__):
        hv = self.__hashvalue
        if hv is None:
            self.__hashvalue = hv = hash(self)
        return hv

    def __add__(self, other, add=tuple.__add__):
        return _HashedTuple(add(self, other))

    def __radd__(self, other, add=tuple.__add__):
        return _HashedTuple(add(other, self))

    def __getstate__(self):
        return {}


_kwmark = (_HashedTuple,)


def _hashkey(*args, **kw):
    if kw:
        return _HashedTuple(args + sum(sorted(kw.items()), _kwmark))
    return _HashedTuple(args)


class _Cache(collections.MutableMapping):
    def __init__(self, maxsize=128):
        self.__data = collections.OrderedDict()
        self.__maxsize = maxsize

    def __getitem__(self, key):
        # Pop the item and re-add it so that the key moves to the end.
        value = self.__data.pop(key)
        self.__data[key] = value
        return value

    def __setitem__(self, key, value):
        maxsize = self.__maxsize
        size = len(self.__data)
        if size >= maxsize:
            nextkey = next(iter(self.__data))
            self.__data.pop(nextkey)
        self.__data[key] = value

    def __delitem__(self, key):
        del self.__data[key]

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)
