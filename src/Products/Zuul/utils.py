##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2021 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import time
import cgi
import transaction

from copy import deepcopy
from types import ClassType
from urlparse import urlparse

from AccessControl import getSecurityManager
from AccessControl.PermissionRole import rolesForPermissionOn
from Acquisition import aq_base, aq_chain
from BTrees.IOBTree import IOBTree
from BTrees.OOBTree import OOBTree
from OFS.PropertyManager import PropertyManager
from zope.i18nmessageid import MessageFactory
from zope.interface import Interface
from ZPublisher.BaseRequest import RequestContainer
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

from Products.ZCatalog.interfaces import ICatalogBrain
from Products.ZenRelations.ZenPropertyManager import (
    ZenPropertyManager,
    iszprop,
)
from Products.ZenUtils.RedisUtils import getRedisClient

log = logging.getLogger("zen.Zuul")

# Translations
ZuulMessageFactory = MessageFactory("zenoss")


def resolve_context(context, default=None, dmd=None):
    """
    Make sure that a given context is an actual object, and not a path to
    the object, by trying to traverse from the dmd if it's a string.
    """
    try:
        dmd = dmd or get_dmd()
    except AttributeError:
        # was not able to get the dmd
        dmd = None
    if dmd:
        if isinstance(context, basestring):
            # Should be a path to the object we want
            if context.startswith("/") and not context.startswith(
                "/zport/dmd"
            ):
                context = context[1:]
            try:
                context = dmd.unrestrictedTraverse(context)
            except (KeyError, AttributeError):
                context = None
    if context is None:
        context = default
    return context


def _mergedLocalRoles(object):
    """
    Replacement for Products.CMFCore.utils._mergedLocalRoles, which raises a
    TypeError in certain situations.
    """
    merged = {}
    object = getattr(object, "aq_inner", object)
    while 1:
        if safe_hasattr(object, "__ac_local_roles__"):
            roles_dict = object.__ac_local_roles__ or {}
            if callable(roles_dict):
                roles_dict = roles_dict()
            for k, v in roles_dict.items():
                if k in merged:
                    merged[k] += list(v)
                else:
                    merged[k] = list(v)
        if safe_hasattr(object, "aq_parent"):
            object = object.aq_parent
            object = getattr(object, "aq_inner", object)
            continue
        if safe_hasattr(object, "im_self"):
            object = object.im_self
            object = getattr(object, "aq_inner", object)
            continue
        break

    return deepcopy(merged)


def allowedRolesAndUsers(context):
    allowed = set()
    for r in rolesForPermissionOn("View", context):
        if isinstance(r, (list, tuple)):
            for x in r:
                allowed.add(x)
        else:
            allowed.add(r)
    for user, roles in _mergedLocalRoles(context).iteritems():
        for role in roles:
            if role in allowed:
                allowed.add("user:" + user)
    if "Owner" in allowed:
        allowed.remove("Owner")
    return list(allowed)


_sevs = ["clear", "debug", "info", "warning", "error", "critical"]


def severityId(severity):
    """Takes an event severity string and returns the "id" of it. As expected
    by the event and the threshold classes
    """
    if isinstance(severity, basestring):
        return _sevs.index(severity.lower())


def severityString(severityId):
    """Takes an event severity id (the numeric value) and converts it to
    the lower case string representation
    """
    if severityId in range(0, 6):
        return _sevs[severityId]


def get_dmd():
    """Retrieve the DMD object."""
    connections = transaction.get()._synchronizers.data.values()[:]
    connections.reverse()
    # Make sure we don't get the temporary connection
    for cxn in connections:
        db = getattr(cxn, "_db", None)
        if db and db.database_name != "temporary":
            resp = HTTPResponse(stdout=None)
            env = {
                "SERVER_NAME": "localhost",
                "SERVER_PORT": "8080",
                "REQUEST_METHOD": "GET",
            }
            req = HTTPRequest(None, env, resp)
            app = cxn.root()["Application"]
            app = app.__of__(RequestContainer(REQUEST=req))
            return app.zport.dmd


_MARKER = object()


def safe_hasattr(object, name):
    return getattr(object, name, _MARKER) is not _MARKER


def unbrain(item):
    if ICatalogBrain.providedBy(item):
        return item.getObject()
    return item


def try_unbrain(item, default=None):
    try:
        return unbrain(item)
    except KeyError:
        if log.getEffectiveLevel() == logging.DEBUG:
            log.warning("catalog object not found in ZODB  uid=%s", item.uid)
        return default


class BrainWhilePossible(object):
    def __init__(self, ob):
        self._ob = ob

    @property
    def _is_brain(self):
        return ICatalogBrain.providedBy(self._ob)

    def __getattr__(self, attr):
        if self._is_brain:
            try:
                return getattr(aq_base(self._ob), attr)
            except AttributeError:
                # Not metadata; time to go get the ob
                self._ob = unbrain(self._ob)
        return getattr(self._ob, attr)


def dottedname(ob):
    # If already a dotted name, just return it
    if isinstance(ob, basestring):
        return ob
    # If an interface, use cached value
    elif isinstance(ob, Interface):
        return ob.__identifier__
    # Don't know, so create name ourselves from the class
    if not isinstance(ob, (type, ClassType)):
        ob = ob.__class__
    return "%s.%s" % (ob.__module__, ob.__name__)


def getZProperties(context):
    """
    Given a context, this function will return all of the ZProperties that
    are defined for this context (ignoring acquisition)
    @returns Dictionary of the form { 'zPropertyName' : 'zPropertyValue',}
    """
    properties = {}
    # make sure we actually have properties
    if not isinstance(context, ZenPropertyManager):
        return properties

    for zprop in filter(iszprop, context.propertyIds()):
        properties[zprop] = PropertyManager.getProperty(context, zprop)
    return properties


def _translateZPropertyValue(zProp, translate, value):
    try:
        return translate(value)
    except Exception as e:
        args = zProp, value, e.__class__.__name__, e
        raise Exception('Unable to translate %s "%s" (%s: %s)' % args)


def getAcquiredZPropertyInfo(obj, zProp, translate=lambda x: x):
    for ancestor in aq_chain(obj)[1:]:
        if isinstance(ancestor, ZenPropertyManager) and ancestor.hasProperty(
            zProp
        ):
            info = {"ancestor": ancestor.titleOrId()}
            try:
                ancestorValue = getattr(ancestor, zProp)
            except AttributeError:
                log.error("Unable to acquire value for %s", zProp)
                continue
            info["acquiredValue"] = _translateZPropertyValue(
                zProp, translate, ancestorValue
            )
            break
    else:
        info = {"acquiredValue": None, "ancestor": None}
    return info


def getZPropertyInfo(
    obj,
    zProp,
    defaultLocalValue="",
    translate=lambda x: x,
    translateLocal=False,
):
    zPropInfo = {}
    zPropInfo["isAcquired"] = not obj.hasProperty(zProp)
    if zPropInfo["isAcquired"]:
        zPropInfo["localValue"] = defaultLocalValue
    else:
        zPropInfo["localValue"] = getattr(obj, zProp)
        if translateLocal:
            zPropInfo["localValue"] = _translateZPropertyValue(
                zProp, translate, zPropInfo["localValue"]
            )
    zPropInfo.update(getAcquiredZPropertyInfo(obj, zProp, translate))
    return zPropInfo


def setZPropertyInfo(obj, zProp, isAcquired, localValue, **kwargs):
    if isAcquired:
        if obj.hasProperty(zProp):
            obj.deleteZenProperty(zProp)
    else:
        if obj.hasProperty(zProp):
            obj._updateProperty(zProp, localValue)
        else:
            obj._setProperty(
                zProp, localValue, type=obj.getPropertyType(zProp)
            )


def allowedRolesAndGroups(context):
    """
    Returns a list of all the groups and
    roles that the logged in user has access too
    @param context: context for which we are retrieving
    allowed roles and groups
    @return [string]: All roles user has as well as groups
    """
    user = getSecurityManager().getUser()
    roles = list(user.getRolesInContext(context))
    # anonymous and anything we own
    roles.append("Anonymous")
    roles.append("user:%s" % user.getId())
    # groups
    groups = user.getGroups()
    for group in groups:
        roles.append("user:%s" % group)

    return roles


def mutateRPN(prefix, knownDatapointNames, rpn):
    """Return a RPN string

    Given a prefix, a list of known datapoints, and an RPN, replace the tokens that are references to other
    datapoints with a prefixed datapoint string.

    >>> _mutateRPN("test", ["test dp1", "test dp2", "test dp3"], "dp1,/,100,*")
    test dp1,/,100,*

    >>> _mutateRPN("test", ["test dp1", "test dp2", "test dp3"], "dp4,/,100,*")
    dp4,/,100,*

    >>> _mutateRPN("test", ["test dp1", "test dp2", "test dp3"], "dp2,+,dp1,/,dp4,-,100,*")
    test dp2,+,test dp1,/,dp4,-,100,*
    """
    newRPN = []
    tokens = rpn.split(",")
    for token in tokens:
        testToken = "%s %s" % (prefix, token)
        if testToken in knownDatapointNames:
            newRPN.append(testToken)
        else:
            newRPN.append(token)
    return ",".join(newRPN)


def sanitizeUrl(url):
    """
    For XSS injections javascript scheme can be used.
    Check if URL scheme is safe and sanitizes URL
    """
    safeSchemes = ["", "http", "https"]

    sanitizedUrl = cgi.escape(url)
    parsedUrl = urlparse(sanitizedUrl)
    if parsedUrl.scheme not in safeSchemes:
        raise ValueError("URL is not valid")

    return sanitizedUrl


class UncataloguedObjectException(Exception):
    """
    The object we've tried to adapt hasn't been indexed
    """

    def __init__(self, ob):
        self.ob = ob
        log.critical(
            "Object %s has not been catalogued. Skipping.",
            ob.getPrimaryUrlPath(),
        )


def catalogAwareImap(f, iterable):
    for ob in iterable:
        try:
            yield f(ob)
        except UncataloguedObjectException:
            pass


class CatalogLoggingFilter(logging.Filter):
    def filter(self, rec):
        return logging.Filter.filter(self, rec) and not self.matches(rec)

    def matches(self, rec):
        return rec.msg.startswith("uncatalogObject unsuccessfully attempted")


class PathIndexCache(object):
    """
    Cache tree search results for further queries.
    """

    def __init__(
        self,
        results,
        instanceresults=None,
        relnames=("devices",),
        treePrefix=None,
    ):
        self._brains = IOBTree()
        self._index = OOBTree()
        self._instanceidx = OOBTree()
        self.insert(self._index, results)
        if instanceresults:
            self.insert(
                self._instanceidx, instanceresults, relnames, treePrefix
            )

    def insert(self, idx, results, relnames=None, treePrefix=None):
        for brain in results:
            rid = brain.getRID()
            path = brain.getPath()
            if treePrefix and not path.startswith(treePrefix):
                paths = brain.global_catalog._catalog.indexes["path"]._unindex[
                    rid
                ]
                for p in paths:
                    if p.startswith(treePrefix):
                        path = p
                        break
            else:
                paths = [path]

            for path in paths:
                path = path.split("/", 3)[-1]
                if relnames:
                    if isinstance(relnames, basestring):
                        relnames = (relnames,)
                    for relname in relnames:
                        path = path.replace("/" + relname, "")
                if rid:  # TODO review this I just did it to avoid exception
                    self._brains[rid] = brain
                    for depth in xrange(path.count("/") + 1):
                        comp = idx.setdefault(path, IOBTree())
                        comp.setdefault(depth, []).append(rid)
                        path = path.rsplit("/", 1)[0]

    def search(self, path, depth=1):
        path = path.split("/", 3)[-1]
        try:
            idx = self._index[path]
            return map(self._brains.get, idx[depth])
        except KeyError:
            return []

    def count(self, path, depth=None):
        path = path.split("/", 3)[-1]
        try:
            idx = self._instanceidx[path]
            if depth is None:
                depth = max(idx.keys())

            # De-duplicate so we don't repeatedly count the same device in
            # multiple sub-organizers.
            unique_keys = set()
            for d in xrange(depth + 1):
                if d not in idx.keys():
                    continue
                for key in idx[d]:
                    unique_keys.add(key)

            return len(unique_keys)
        except KeyError:
            return 0

    @classmethod
    def test(self, dmd):
        from Products.Zuul.catalog.interfaces import IModelCatalogTool

        results = IModelCatalogTool(dmd.Devices).search(
            "Products.ZenModel.DeviceOrganizer.DeviceOrganizer"
        )
        instances = IModelCatalogTool(dmd.Devices).search(
            "Products.ZenModel.Device.Device"
        )
        tree = PathIndexCache(results, instances, "devices")
        print(tree)


class RedisGraphLinksTool(object):
    """
    Connect to Redis, put graph config and get it by hash
    """

    REDIS_RECONNECTION_INTERVAL = 3
    # config of graph will be deleted after 90 days without calling
    EXPIRATION_TIME = 60 * 60 * 24 * 90

    def __init__(self):
        self._redis_client = None
        self._redis_last_connection_attemp = 0

    @staticmethod
    def create_redis_client():
        client = None
        try:
            client = getRedisClient()
            client.config_get()  # test the connection
        except Exception as e:
            log.warning("Exception trying to connect to redis: %s", e)
            client = None
        return client

    def _connected_to_redis(self):
        """Ensures we have a connection to redis"""
        if self._redis_client is None:
            now = time.time()
            if (
                now - self._redis_last_connection_attemp
                > self.REDIS_RECONNECTION_INTERVAL
            ):
                log.debug("Trying to reconnect to redis")
                self._redis_last_connection_attemp = now
                self._redis_client = self.create_redis_client()
                if self._redis_client:
                    log.debug("Connected to redis")
        return self._redis_client is not None

    def push_to_redis(self, string, data):
        key = "graphLink:" + string
        if not self._connected_to_redis():
            return False
        try:
            self._redis_client.set(key, data)
            self._redis_client.expire(key, self.EXPIRATION_TIME)
            log.debug("Success pushed to Redis")
            return True
        except Exception as e:
            log.warning("Exception trying to push data to redis: %s", e)
            self._redis_client = None
            return False

    def load_from_redis(self, string):
        key = "graphLink:" + string
        if not self._connected_to_redis():
            return None
        try:
            self._redis_client.expire("graphLink:" + key, self.EXPIRATION_TIME)
            data = self._redis_client.get(key)
            log.debug("Success received data for key %s from Redis", key)
            return data
        except Exception as e:
            log.warning("Exception trying to receive data from redis: %s", e)
            self._redis_client = None
            return None
