##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from cgi import escape

from collections import defaultdict
from contextlib import contextmanager

import zExceptions

from Acquisition import aq_base
from AccessControl import getSecurityManager
from decorator import decorator
from Products.ZCatalog.ZCatalog import ZCatalog
from ZODB.POSException import ConflictError
from zope.component import adapts
from zope.interface import ro, implements

from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.IpInterface import IpInterface
from Products.ZenUtils.IpUtil import ipToDecimal
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.Search import makeMultiPathIndex
from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseSensitiveKeywordIndex
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.Device import Device
from Products.ZenModel.FileSystem import FileSystem
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.Zuul.utils import getZProperties, allowedRolesAndUsers

from .interfaces import (
    IGlobalCatalogFactory,
    IGloballyIndexed,
    IPathReporter,
    IIndexableWrapper,
)

_MARKER = object()
_CACHE = defaultdict(dict)
_CACHE_RESULTS = []

globalCatalogId = "global_catalog"


def _allowedRoles(user):
    roles = list(user.getRoles())
    roles.append("Anonymous")
    roles.append("user:%s" % user.getId())
    return roles


def _escape(s, quote=None):
    """
    Wrapper around `cgi.escape` to return empty string on `None` or
    empty string.
    """
    return escape(s, quote=quote) if s else ""


@contextmanager
def catalog_caching():
    """
    The C{memoized_in_context} decorator will apply throughout the lifetime of
    this context manager.
    """
    try:
        _CACHE_RESULTS.append(1)
        yield
    finally:
        _CACHE_RESULTS.pop()
        if not _CACHE_RESULTS:
            _CACHE.clear()


@decorator
def memoized_in_context(f, wrapper, *args, **kwargs):
    """
    Memoize the result of an IndexableWrapper property as long as CACHE_RESULTS
    is True (that is, inside the C{catalog_caching} context manager, above).

    Results will be memoized on a per-wrapped-object basis (two different
    IndexableWrapper instances wrapping the same object will use the same cache
    for the same method).
    """
    if _CACHE_RESULTS:
        path = wrapper.getPath()
        result = _CACHE[path].get(f.__name__, _MARKER)
        if result is _MARKER:
            result = f(wrapper, *args, **kwargs)
            _CACHE[path][f.__name__] = result
        return result
    return f(wrapper, *args, **kwargs)


class IndexableWrapper(object):
    implements(IIndexableWrapper)
    adapts(IGloballyIndexed)

    def __init__(self, context):
        self._context = context

    def __getattr__(self, name):
        return getattr(self._context, name)

    def getObject(self):
        return self._context

    def getPath(self):
        return self._context.getPrimaryId()

    def allowedRolesAndUsers(self):
        """
        Roles and users with View permission.

        This is a KeywordIndex on the catalog.
        """
        return allowedRolesAndUsers(self._context)

    def objectImplements(self):
        """
        All interfaces and classes implemented by an object.

        This is a KeywordIndex on the catalog.
        """
        dottednames = set()
        # Add the highest five classes in resolution order. 5 is
        # an arbitrary number; essentially, we only care about indexing
        # Zenoss classes, and our inheritance tree isn't that deep. Past
        # 5 we index a bunch of ObjectManager, Persistent, etc., which
        # we'll never use, and enact a significant performance penalty
        # when inserting keywords into the index.

        for kls in ro.ro(self._context.__class__):
            # @TODO review. had some issues with picking only the top 5
            # instead we get anything from Products or Zenpacks
            if kls.__module__.startswith(
                "Products"
            ) or kls.__module__.startswith("ZenPacks"):
                dottednames.add("%s.%s" % (kls.__module__, kls.__name__))
        return list(dottednames)

    @property
    def ipAddress(self):
        """
        IP address associated with this object as 32-bit integer. For devices,
        the manageIp; for interfaces, the first ip address.

        This is a FieldIndex on the catalog.
        """
        if isinstance(self._context, IpNetwork):
            return
        getIp = getattr(self._context, "getIpAddress", None)
        if getIp is None:
            getIp = getattr(self._context, "getManageIp", None)
        if getIp is None:
            return
        ip = getIp()
        if ip:
            ip = ip.partition("/")[0]
            return str(ipToDecimal(ip))

    @property
    def zProperties(self):
        """
        A dictionary of all the zProperties associated with this device.
        In the form:
          { 'zCommandTimeOut' : 180 }

        This is on the metadata of the catalog
        """
        return getZProperties(self._context)

    def uid(self):
        """
        Primary path for this object. This is included for sorting purposes;
        obviously it would normally be totally unnecessary, due to
        brain.getPath() being available.

        This is a FieldIndex on the catalog.
        """
        return aq_base(self._context).getPrimaryId()

    def path(self):
        """
        Paths under which this object may be found. Subclasses should provide
        tuples indicating more paths (e.g. via a ToMany relationship).

        This is a MultiPathIndex on the catalog.
        """
        return IPathReporter(self._context).getPaths()

    def name(self):
        """
        The name of the object.
        """
        try:
            return self._context.titleOrId()
        except AttributeError:
            return self._context.id

    def meta_type(self):
        """
        Object's meta_type. Mostly used for backwards compatibility.

        This is a FieldIndex on the catalog and a metadata column.
        """
        return aq_base(self._context).meta_type

    def uuid(self):
        """
        Object's uuid. This is a metadata column.
        """
        try:
            # We don't need create() to update the global catalog, because by definition
            # this is only called when the object is going to be indexed.
            return IGlobalIdentifier(self._context).create(
                update_global_catalog=False
            )
        except ConflictError:
            raise
        except Exception:
            pass

    def productionState(self):
        """
        Production state. Only for Devices.
        """

    def collectors(self):
        """
        Collectors. Only for Components.
        """

    def monitored(self):
        """
        Whether or not monitored. Only for Components.
        """

    def searchKeywordsForChildren(self):
        """
        For searchables
        """

    def searchKeywords(self):
        """
        For searchables
        """

    def searchExcerpt(self):
        """
        For searchables
        """

    def searchIcon(self):
        """
        For searchables
        """

    def macAddresses(self):
        """
        Mac Address. Devices and Interfaces
        """


class SearchableMixin(object):
    def searchKeywordsForChildren(self):
        return (self._context.titleOrId(),)

    def searchKeywords(self):
        o = self._context
        return self.searchKeywordsForChildren() + (o.meta_type,)

    def searchExcerpt(self):
        return _escape(self._context.titleOrId())

    def searchIcon(self):
        return self._context.getIconPath()


class ComponentWrapper(SearchableMixin, IndexableWrapper):
    adapts(DeviceComponent)

    def monitored(self):
        if self._context.monitored():
            return "1"
        return ""

    def collectors(self):
        return self._context.getCollectors()

    def searchKeywordsForChildren(self):
        o = self._context
        return (
            o.titleOrId(),
            o.name(),
            o.monitored() and "monitored" or "unmonitored",
        ) + IIndexableWrapper(o.device()).searchKeywordsForChildren()

    def searchExcerpt(self):
        o = self._context
        return '%s <span style="font-size:smaller">(%s)</span>' % (
            _escape(o.name()),
            _escape(o.device().titleOrId()),
        )


class DeviceWrapper(SearchableMixin, IndexableWrapper):
    adapts(Device)

    def macAddresses(self):
        return self._context.getMacAddresses()

    def productionState(self):
        return self._context.getProductionState()

    @memoized_in_context
    def searchKeywordsForChildren(self):
        o = self._context
        ipAddresses = []
        # TODO: What to do about IP addresses?
        # try:
        #     # If we find an interface IP address, link it to a device
        #     if hasattr(o, 'os') and hasattr(o.os, 'interfaces'):
        #         ipAddresses = chain(*(iface.getIpAddresses()
        #                                for iface in o.os.interfaces()))
        #         # fliter out localhost-ish addresses
        #         ipAddresses = ifilterfalse(lambda x: x.startswith('127.0.0.1/') or
        #                                              x.startswith('::1/'),
        #                                    ipAddresses)
        # except Exception:
        #     ipAddresses = []

        return (
            (
                o.titleOrId(),
                o.manageIp,
                o.hw.serialNumber,
                o.hw.tag,
                o.getHWManufacturerName(),
                o.getHWProductName(),
                o.getOSProductName(),
                o.getOSManufacturerName(),
                o.getHWSerialNumber(),
                o.getPerformanceServerName(),
                o.getProductionStateString(),
                o.getPriorityString(),
                o.getLocationName(),
                o.monitorDevice() and "monitored" or "unmonitored",
            )
            + tuple(o.getSystemNames())
            + tuple(o.getDeviceGroupNames())
            + tuple(ipAddresses)
            + (self._context.snmpSysName, self._context.snmpLocation)
        )

    def searchExcerpt(self):
        o = self._context
        if o.manageIp:
            return '%s <span style="font-size:smaller">(%s)</span>' % (
                _escape(o.titleOrId()),
                o.manageIp,
            )
        else:
            return _escape(o.titleOrId())


class IpInterfaceWrapper(ComponentWrapper):
    """
    Allow searching by (from remote device) user-configured description
    """

    adapts(IpInterface)

    def macAddresses(self):
        return [self._context.macaddress]

    def searchKeywordsForChildren(self):
        """
        When searching, what things to search on
        """
        if self._context.titleOrId() in ("lo", "sit0"):
            # Ignore noisy interfaces
            return ()
        # We don't need to include the ip addresses for this interface, because
        # all ips on a device are included in the keywords of every one of its
        # components.
        return super(IpInterfaceWrapper, self).searchKeywordsForChildren() + (
            self._context.description,
        )

    def searchExcerpt(self):
        """
        How the results are displayed in the search drop-down
        """
        return (
            super(IpInterfaceWrapper, self).searchExcerpt()
            + " "
            + _escape(
                " ".join(
                    [
                        self._context.description,
                    ]
                )
            )
        )


class FileSystemWrapper(ComponentWrapper):
    adapts(FileSystem)

    def name(self):
        return self._context.name()


class DeviceOrganizerWrapper(SearchableMixin, IndexableWrapper):
    adapts(DeviceOrganizer)

    def searchKeywords(self):
        obj = self._context
        return (obj.getOrganizerName(), str(obj.description))

    def searchExcerpt(self):
        return _escape(self._context.getOrganizerName())

    def searchIcon(self):
        return "/zport/dmd/img/icons/folder.png"


class GlobalCatalog(ZCatalog):
    id = globalCatalogId

    def __init__(self):
        ZCatalog.__init__(self, self.id)

    def searchResults(self, **kw):
        user = getSecurityManager().getUser()
        kw["allowedRolesAndUsers"] = _allowedRoles(user)
        return ZCatalog.searchResults(self, **kw)

    def unrestrictedSearchResults(self, **kw):
        return ZCatalog.searchResults(self, **kw)

    def catalog_object(self, obj, uid=None, **kwargs):
        if not isinstance(obj, self._get_forbidden_classes()):
            ob = IIndexableWrapper(obj)
            if kwargs.get("idxs"):
                # the first time we catalog an object we must catalog the
                # entire object
                uid = uid or "/".join(obj.getPhysicalPath())
                if not uid in self._catalog.uids:
                    del kwargs["idxs"]

            ZCatalog.catalog_object(self, ob, uid, **kwargs)

    def uncatalog_object(self, path):
        try:
            # If path points to an object, we can ignore the uncataloguing if
            # it's a forbidden class (because it was never indexed in the first
            # place)
            obj = self.unrestrictedTraverse(path)
            if not isinstance(obj, self._get_forbidden_classes()):
                super(GlobalCatalog, self).uncatalog_object(path)
        except (KeyError, zExceptions.NotFound):
            # Can't find the object, so maybe a bad path or something; just get
            # rid of it
            super(GlobalCatalog, self).uncatalog_object(path)

    def index_object_under_paths(self, obj, paths):
        if not isinstance(obj, self._get_forbidden_classes()):
            p = "/".join(obj.getPrimaryPath())
            uid = self._catalog.uids.get(p, None)
            if uid:
                idx = self._catalog.getIndex("path")
                idx.index_paths(uid, paths)

    def unindex_object_from_paths(self, obj, paths):
        p = "/".join(obj.getPrimaryPath())
        uid = self._catalog.uids.get(p, None)
        if uid:
            idx = self._catalog.getIndex("path")
            idx.unindex_paths(uid, paths)

    def getIndexes(self):
        return self._catalog.indexes

    def _get_forbidden_classes(self):
        return (Software, OperatingSystem)

    def hasIndexForTypes(self, types, index):
        """
        @param types: List of python types (unused)
        @param index: index we are inquiring if it exists
        @return: boolean if have this index and can filter/sort on it without waking up the objects
        """
        cat = self._catalog
        return cat.indexes.get(index)

    def addIndex(self, id, index, extra=None):
        """
        Dispatches to self._catalog.addIndex
        """
        return self._catalog.addIndex(id, index)


def initializeGlobalCatalog(catalog):
    catalog.addIndex("id", makeCaseSensitiveFieldIndex("id"))
    catalog.addIndex("uid", makeCaseSensitiveFieldIndex("uid"))
    catalog.addIndex("meta_type", makeCaseSensitiveFieldIndex("meta_type"))
    catalog.addIndex("name", makeCaseInsensitiveFieldIndex("name"))
    catalog.addIndex("ipAddress", makeCaseSensitiveFieldIndex("ipAddress"))
    catalog.addIndex(
        "objectImplements", makeCaseSensitiveKeywordIndex("objectImplements")
    )
    catalog.addIndex(
        "allowedRolesAndUsers",
        makeCaseSensitiveKeywordIndex("allowedRolesAndUsers"),
    )
    catalog.addIndex("monitored", makeCaseSensitiveFieldIndex("monitored"))
    catalog.addIndex("path", makeMultiPathIndex("path"))
    catalog.addIndex("collectors", makeCaseSensitiveKeywordIndex("collectors"))
    catalog.addIndex(
        "productKeys", makeCaseSensitiveKeywordIndex("productKeys")
    )
    catalog.addIndex(
        "searchKeywords", makeCaseInsensitiveKeywordIndex("searchKeywords")
    )
    catalog.addIndex(
        "macAddresses", makeCaseInsensitiveKeywordIndex("macAddresses")
    )

    catalog.addColumn("id")
    catalog.addColumn("uuid")
    catalog.addColumn("name")
    catalog.addColumn("meta_type")
    catalog.addColumn("monitored")
    catalog.addColumn("collectors")
    catalog.addColumn("zProperties")
    catalog.addColumn("searchIcon")
    catalog.addColumn("searchExcerpt")


class GlobalCatalogFactory(object):
    implements(IGlobalCatalogFactory)

    def create(self, portal):
        from Products.Zuul.catalog.legacy import LegacyCatalogAdapter

        catalog = LegacyCatalogAdapter(portal.dmd, globalCatalogId)
        self.setupCatalog(portal, catalog)

    def setupCatalog(self, portal, catalog):
        portal._setObject(globalCatalogId, catalog)

    def remove(self, portal):
        portal._delObject(globalCatalogId)
