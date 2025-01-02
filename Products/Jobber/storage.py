##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import json
import logging
import re
import types

from collections import Container, Iterable, Sized

import six

from celery import states as celery_states

from Products.ZenUtils.RedisUtils import getRedisClient

from .config import ZenCeleryConfig

_appkey = "zenjobs"
_createdkey = "{}:created".format(_appkey)
_startedkey = "{}:started".format(_appkey)
_finishedkey = "{}:finished".format(_appkey)

_jobkey_template = "{}:job:{{}}".format(_appkey)
_statuskey_template = "{}:status:{{}}".format(_appkey)
_useridkey_template = "{}:userid:{{}}".format(_appkey)

_alljobkeys = _jobkey_template.format("*")
_allstatuskeys = _statuskey_template.format("*")
_alluseridkeys = _useridkey_template.format("*")


log = logging.getLogger("zen.zenjobs")


def makeJobStore():
    """Create and return the ZenJobs JobStore client."""
    client = getRedisClient(url=ZenCeleryConfig.result_backend)
    return JobStore(client, expires=ZenCeleryConfig.result_expires)


class _Converter(object):
    __slots__ = ("dumps", "loads")

    def __init__(self, dumps, loads):
        self.dumps = dumps
        self.loads = loads


def _float_str(f):
    return "{:.6f}".format(f).strip("0")


def _immutable(self, *args, **kw):
    raise TypeError("Object is immutable")


class _Fields(dict):
    """Describes all the attributes of a job record.

    The keys are the names of the attributes and the values are tuples
    containing the encode and encode functions for the attribute value.

    Redis stores everything as strings, including integers and floats.
    """

    def __init__(self):
        super(_Fields, self).__init__(
            (
                ("jobid", _Converter(str, str)),
                ("name", _Converter(str, str)),
                ("summary", _Converter(str, str)),
                ("description", _Converter(str, str)),
                ("userid", _Converter(str, str)),
                ("logfile", _Converter(str, str)),
                ("created", _Converter(_float_str, float)),
                ("started", _Converter(_float_str, float)),
                ("finished", _Converter(_float_str, float)),
                ("status", _Converter(str, str)),
                ("details", _Converter(json.dumps, json.loads)),
            )
        )

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


Fields = _Fields()


class _Any(object):
    """Mimics the 'in' operator's behavior via equality comparison.

    Returns True if the given value matches any of the initialized values.
    E.g.

        okvalues = _Any("foo", "bar", "baz")
        assert "foo" == okvalues
    """

    def __init__(self, *matches):
        if not all(isinstance(m, six.string_types) for m in matches):
            raise ValueError(
                "All values must be strings %s" % (matches,),
            )
        self.__matches = matches

    def __eq__(self, other):
        return any((m == other) for m in self.__matches)

    def __ne__(self, other):
        return not self.__eq__(other)


class _RegEx(object):
    """Applies a regular expression object using equality comparison.

    Returns True if the given value regular expression object's search
    method returns True. E.g.

        expr = _RegEx(re.compile("lan_c"))
        assert expr == "lan_c120_3v"
    """

    def __init__(self, expr):
        self.__expr = expr

    def __eq__(self, other):
        return self.__expr.search(other) is not None


class JobStore(Container, Iterable, Sized):
    """Implements an API for managing zenjobs' job data.

    If 'expires' is given, keys are not marked for expiration until their
    associated tasks have finished execution.
    """

    def __init__(self, client, expires=None):
        """Initialize a JobStore instance.

        :param client: A Redis client instance.
        :type client: redis.StrictRedis
        :param expires: The number of seconds a key will exist.
        :type expires: Union[int, None]
        """
        self.__client = client
        self.__expires = expires
        self.__scan_count = 1000

    def search(self, **fields):
        """Return the job IDs for jobs matching the search criteria.

        The job IDs are returned as an iterable.

        The field value(s) may be a string, a float, a sequence of strings,
        or a regular expression.  All other values will raise a TypeError
        exception.

        Specifying a field that does not exist in a record will raise an
        AttributeError exception.

        :param fields: The search criteria by field name.
        :type fields: Mapping[str, Union[str, float, RegEx, Interable[str]]]
        :return: The IDs for jobs matching the search criteria.
        :rtype: Iterable[str]
        :raises TypError: if an unsupported value type is given for a field
        """
        _verifyfields(fields.keys())

        statuses = fields.pop("status", ())
        if statuses:
            if isinstance(statuses, six.string_types):
                statuses = (statuses,)
            elif isinstance(statuses, types.GeneratorType):
                statuses = tuple(statuses)

        userids = fields.pop("userid", ())
        if userids:
            if isinstance(userids, six.string_types):
                userids = (userids,)
            elif isinstance(userids, types.GeneratorType):
                userids = tuple(userids)

        if not fields:
            result = self._index_lookup(statuses, userids)
            if result is not None:
                return result
        return self._index_and_record_lookup(statuses, userids, fields)

    def _index_lookup(self, statuses, userids):
        if len(statuses) > 1 or len(userids) > 1:
            return
        status = statuses[0] if statuses else None
        userid = userids[0] if userids else None
        if status and not userid:
            return (
                jobid
                for jobid in self.__client.sscan_iter(
                    _statuskey(status), count=self.__scan_count
                )
            )
        if userid and not status:
            return (
                jobid
                for jobid in self.__client.sscan_iter(
                    _useridkey(userid), count=self.__scan_count
                )
            )
        return (
            jobid
            for jobid in self.__client.sinter(
                _statuskey(status), _useridkey(userid)
            )
        )

    def _index_and_record_lookup(self, statuses, userids, fields):
        result = self._index_lookup(statuses, userids)
        jobids = set() if result is None else set(result)

        if not jobids:
            jobids.update(self._get_jobids_by_index(_statuskey, statuses))
            jobids.update(self._get_jobids_by_index(_useridkey, userids))

        matchers = self._get_matchers(fields)

        if jobids:
            if not fields:
                return jobids
            return (
                jobid
                for jobid in jobids
                if self._match_fields(matchers, _jobkey(jobid), fields.keys())
            )
        return (
            self.__client.hget(key, "jobid")
            for key in self.__client.scan_iter(
                match=_alljobkeys, count=self.__scan_count
            )
            if self._match_fields(matchers, key, fields.keys())
        )

    def _get_matchers(self, fields):
        matchers = {}
        for name, value in fields.items():
            # Note: check for string first because strings are iterable.
            if isinstance(value, six.string_types):
                matchers[name] = value
            elif isinstance(value, Iterable):
                matchers[name] = _Any(*value)
            elif isinstance(value, re._pattern_type):
                matchers[name] = _RegEx(value)
            elif isinstance(value, float):
                matchers[name] = "{:f}".format(value)
            else:
                raise TypeError(
                    "Type '%s' not supported for field '%s'"
                    % (type(value), name),
                )
        return matchers

    def _match_fields(self, matchers, jobkey, fieldnames):
        if not fieldnames:
            return ()
        record = dict(
            zip(fieldnames, self.__client.hmget(jobkey, *fieldnames))
        )
        return matchers == record

    def _get_jobids_by_index(self, keyfactory, indexids):
        if not indexids:
            return ()
        return (
            jobid
            for key in (keyfactory(indexid) for indexid in indexids)
            for jobid in self.__client.sscan_iter(key, count=self.__scan_count)
        )

    def getfield(self, jobid, name, default=None):
        """Return the field value in the job data identified by jobid.

        If jobid does not identify a job, the default value is returned.

        If the named field does not exist, an AttributeError
        exception is raised.

        :param str jobid: the job ID
        :param str name: the name of a field in the job data
        :return: the value of field or the default value
        :rtype: Any
        :raise AttributeError: if name is not a known field
        """
        if name not in Fields:
            raise AttributeError("Job record has no attribute '%s'" % name)
        key = _jobkey(jobid)
        if not self.__client.exists(key):
            return default
        raw = self.__client.hget(key, name)
        if raw is None:
            return default
        return Fields[name].loads(raw)

    def update(self, jobid, **fields):
        """Set the field values on the identified job.

        If jobid does not identify a job, a KeyError exception is raised.

        If a field name does not identify a known field, an AttributeError
        exception is raised.

        :type jobid: str
        :param fields: Mapping[str, Union[str, float, int, dict]]
        :raises: Union[AttributeError, KeyError]
        """
        badfields = fields.viewkeys() - Fields.viewkeys()
        if badfields:
            raise AttributeError(
                "Job record has no attribute%s %s"
                % (
                    "" if len(badfields) == 1 else "s",
                    ", ".join("'%s'" % name for name in badfields),
                ),
            )
        jobkey = _jobkey(jobid)
        if not self.__client.exists(jobkey):
            raise KeyError("Job not found: %s" % jobid)
        oldstatus, olduserid = self.__client.hmget(
            jobkey, ("status", "userid")
        )
        deleted_fields = [k for k, v in fields.items() if v is None]
        if deleted_fields:
            self.__client.hdel(jobkey, *deleted_fields)
        fields = {
            k: Fields[k].dumps(v) for k, v in fields.items() if v is not None
        }
        if fields:
            self.__client.hmset(jobkey, fields)
        newstatus, newuserid = self.__client.hmget(
            jobkey, ("status", "userid")
        )
        self._update_status_index(jobid, oldstatus, newstatus)
        self._update_userid_index(jobid, olduserid, newuserid)
        self.__expire_key_if_status_is_ready(jobkey)

    def _update_status_index(self, jobid, oldstatus, newstatus):
        if newstatus == oldstatus:
            return
        if oldstatus:
            oldstatuskey = _statuskey(oldstatus)
            self.__client.srem(oldstatuskey, jobid)
        if newstatus:
            newstatuskey = _statuskey(newstatus)
            self.__client.srem(newstatuskey, jobid)

    def _update_userid_index(self, jobid, olduserid, newuserid):
        if newuserid == olduserid:
            return
        if olduserid:
            olduseridkey = _useridkey(olduserid)
            self.__client.srem(olduseridkey, jobid)
        if newuserid:
            newuseridkey = _useridkey(newuserid)
            self.__client.srem(newuseridkey, jobid)

    def keys(self):
        """Return all existing job IDs.

        :rtype: Iterator[str]
        """
        return (
            self.__client.hget(key, "jobid")
            for key in self.__client.scan_iter(
                match=_alljobkeys, count=self.__scan_count
            )
        )

    def values(self):
        """Return all existing job data.

        :rtype: Iterator[Dict[str, Union[str, float]]]
        """
        items = _iteritems(self.__client, self.__scan_count)
        return (
            {k: Fields[k].loads(v) for k, v in fields.iteritems()}
            for _, fields in items
        )

    def items(self):
        """Return all existing jobs as (ID, data) pairs.

        :rtype: Iterator[Tuple[str, Dict[str, Union[str, float]]]]
        """
        items = _iteritems(self.__client, self.__scan_count)
        return (
            (
                fields["jobid"],
                {k: Fields[k].loads(v) for k, v in fields.iteritems()},
            )
            for _, fields in items
        )

    def mget(self, *jobids):
        """Return job data for each provided job ID.

        The returned iterable will produce the job data in the same
        order given in the jobids parameter.

        :param jobids: Iterable[str]
        :rtype: Iterator[Dict[str, Union[str, float]]]
        """
        keys = (_jobkey(jobid) for jobid in jobids)
        raw = (
            self.__client.hgetall(key)
            for key in keys
            if self.__client.exists(key)
        )
        return (
            {k: Fields[k].loads(v) for k, v in item.iteritems()}
            for item in raw
        )

    def get(self, jobid, default=None):
        """Return the job data for the given job ID.

        If the job ID is not found, the default argument is returned.

        :type jobid: str
        :type default: Any
        :rtype: Union[Dict[str, Union[str, float]], default]
        """
        key = _jobkey(jobid)
        if not self.__client.exists(key):
            return default
        item = self.__client.hgetall(key)
        return {k: Fields[k].loads(v) for k, v in item.iteritems()}

    def __getitem__(self, jobid):
        """Return the job data for the given job ID.

        If the job ID is not found, a KeyError exception is raised.

        :type jobid: str
        :rtype: Dict[str, Union[str, float]]
        :raises: KeyError
        """
        key = _jobkey(jobid)
        if not self.__client.exists(key):
            raise KeyError("Job not found: %s" % jobid)
        item = self.__client.hgetall(key)
        return {k: Fields[k].loads(v) for k, v in item.iteritems()}

    def __setitem__(self, jobid, data):
        """Insert or replace the job data for the given job ID.

        If the data contains unknown fields, a ValueError exception is raised.

        :param jobid: str
        :param data: Mapping[str, Union[str, float]]
        :raises: ValueError
        """
        _verifyfields(data.keys())
        data = {
            k: Fields[k].dumps(v) for k, v in data.items() if v is not None
        }
        key = _jobkey(jobid)
        olddata = self.__client.hgetall(key)
        deleted_fields = set(olddata) - set(data)
        if deleted_fields:
            self.__client.hdel(key, *deleted_fields)
        self.__client.hmset(key, data)

        # Update userid index
        userid = data.get("userid")
        if userid:
            userid_key = _useridkey(userid)
            self.__client.sadd(userid_key, jobid)

        # Update status index
        status = data.get("status")
        if status:
            status_key = _statuskey(status)
            self.__client.sadd(status_key, jobid)

        self.__expire_key_if_status_is_ready(key)

    def mdelete(self, *jobids):
        """Delete the job data associated with each of the given job IDs.

        :param jobsids: An iterable producing Job IDs
        :type jobids: Iterable[str]
        """
        if not jobids:
            return
        jobkeys = (_jobkey(jobid) for jobid in jobids)
        self.__client.delete(*jobkeys)
        for statuskey in self.__client.scan_iter(
            _allstatuskeys, count=self.__scan_count
        ):
            self.__client.srem(statuskey, *jobids)
        for useridkey in self.__client.scan_iter(
            _alluseridkeys, count=self.__scan_count
        ):
            self.__client.srem(useridkey, *jobids)

    def __delitem__(self, jobid):
        """Delete the job data associated with the given job ID.

        If the job ID does not exist, a KeyError is raised.

        :type jobid: str
        """
        jobkey = _jobkey(jobid)
        if not self.__client.exists(jobkey):
            for statuskey in self.__client.scan_iter(
                _allstatuskeys, count=self.__scan_count
            ):
                self.__client.srem(statuskey, jobid)
            for useridkey in self.__client.scan_iter(
                _alluseridkeys, count=self.__scan_count
            ):
                self.__client.srem(useridkey, jobid)
            raise KeyError("Job not found: %s" % jobid)

        status = self.__client.hget(jobkey, "status")
        if status:
            statuskey = _statuskey(status)
            self.__client.srem(statuskey, jobid)

        userid = self.__client.hget(jobkey, "userid")
        if userid:
            useridkey = _useridkey(userid)
            self.__client.srem(useridkey, jobid)

        self.__client.delete(jobkey)

    def __contains__(self, jobid):
        """Return True if job data exists for the given job ID.

        :type jobid: str
        :rtype: boolean
        """
        return self.__client.exists(_jobkey(jobid))

    def __len__(self):
        return sum(
            1
            for _ in self.__client.scan_iter(
                match=_alljobkeys, count=self.__scan_count
            )
        )

    def __iter__(self):
        """Return an iterator producing all the job IDs in the datastore.

        :rtype: Iterator[str]
        """
        return self.keys()

    def ttl(self, jobid):
        result = self.__client.ttl(_jobkey(jobid))
        return result if result >= 0 else None

    def __expire_key_if_status_is_ready(self, key):
        status = self.__client.hget(key, "status")
        if self.__expires and status in celery_states.READY_STATES:
            self.__client.expire(key, self.__expires)


def _jobkey(jobid):
    """Return the redis key for the given job ID."""
    return _jobkey_template.format(jobid)


def _statuskey(status):
    """Return the redis key for the given status."""
    return _statuskey_template.format(status)


def _useridkey(userid):
    """Return the redis key for the given user ID."""
    return _useridkey_template.format(userid)


def _iteritems(client, count):
    """Return an iterable of (redis key, job data) pairs.

    Only (key, data) pairs where data is not None are returned.
    """
    keys = client.scan_iter(match=_alljobkeys, count=count)
    raw = ((key, client.hgetall(key)) for key in keys)
    return ((key, data) for key, data in raw if data)


def _verifyfields(fields):
    bad_fields = set(fields) - set(Fields)
    if len(bad_fields):
        raise AttributeError(
            "Invalid field%s %s"
            % (
                "" if len(bad_fields) == 1 else "s",
                ", ".join("'%s'" % n for n in bad_fields),
            )
        )
