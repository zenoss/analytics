##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in 
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
The Zuul module presents two APIs. One is an internal Python API and the other
is a remote JSON API.  The code that presents the JSON API is built on top of
the Python API. The Python API can be used to extend Zenoss with code that
runs within zopectl, zenhub, or zendmd. The Python API is made up of multiple
facades representing the various aspects of the Zenoss domain model. Each
facade supplies methods that allow the user to retrieve and manipulate
information stored in the Zope object database, the MySQL database, and the
RRDtool data files.  The facades return simple info objects (similar to Java
beans) that primarily contain a set of properties. Each info object adapts a
particular class from the ZenModel module.

The JSON API adheres to the Ext Direct protocol
(http://www.sencha.com/products/extjs/extdirect). The Ext JS library makes it
very easy to work with this protocol, but the data format is simple and it
could be easily consumed within other javascript frameworks or clients written
in any language that has a JSON library.  The JSON API is implented by
multiple routers, which for the most part, map one-to-one with the Python API
facades.  The routers use the marshalling module included in Zuul to transform
the info objects returned by the facade into a Python data structure can be 
dumped to a JSON formatted string by the Python json module. The marshalling
module also provides the capability of binding the values in a Python data
structure loaded by the Python json module to the properties of a Zuul info
object.  
"""

import AccessControl
import logging
from OFS.ObjectManager import ObjectManager
from zope import component
from zope.interface import verify
from zope.event import notify 
from interfaces import IFacade, IInfo
from interfaces import IMarshallable
from interfaces import IMarshaller
from interfaces import IUnmarshaller
from utils import safe_hasattr as hasattr, get_dmd
from BTrees.OOBTree import OOSet
from Products.ZenWidgets import messaging
from Products.Zuul.catalog.events import IndexingEvent
from DateTime import DateTime


def getFacade(name, context=None):
    """
    Get facade by name.  The names are documented in configure.zcml defined as
    utilities that provide subclasses of IFacade (all the subclasses follow
    the naming convention I*Facade). This function hides the use of Zope
    Component Architecture (ZCA) from the Ext Direct routers and other
    consumers of the Zuul Python API.
    """
    if context is None:
        context = get_dmd()
    return component.getAdapter(context, IFacade, name)


def listFacades(context=None):
    """
    Provide a list of all known facades.
    """
    if context is None:
        context = get_dmd()
    return sorted(str(name) for name, obj in component.getAdapters([context], IFacade))


class AlreadySeenException(Exception):
    pass


def marshal(obj, keys=None, marshallerName='', objs=None):
    """
    Convert an object to a dictionary. keys is an optional list of keys to
    include in the returned dictionary.  if keys is None then all public
    attributes are returned.  marshallerName is an optional marshalling
    adapter name. if it is an empty string then the default marshaller will be
    used.
    """
    #to prevent recursing back over something twice, keep track of seen objs
    if objs is None:
        objs = OOSet()

    # obj is itself marshallable, so make a marshaller and marshal away
    if IMarshallable.providedBy(obj):
        marshaller = component.getAdapter(obj, IMarshaller, marshallerName)
        verify.verifyObject(IMarshaller, marshaller)

        # Import here to avoid recursive import syndrome.
        from Products.Zuul.infos import InfoBase

        if isinstance(obj, InfoBase):
            key = (getattr(obj._object, '_p_oid', id(obj)), obj.__class__)
            if key in objs:
                raise AlreadySeenException()
            else:
                objs.insert(key)
                try:
                    return marshal(marshaller.marshal(keys),
                            keys, marshallerName, objs)
                except AlreadySeenException:
                    pass
                finally:
                    objs.remove(key)
        else:
            return marshal(marshaller.marshal(keys), keys, marshallerName, objs)


    # obj is a dict, so marshal its values recursively
    # Zuul.marshal({'foo':1, 'bar':2})
    if isinstance(obj, dict):
        marshalled_dict = {}
        for k in obj:
            try:
                marshalled_dict[k] = marshal(obj[k], keys, marshallerName, objs)
            except AlreadySeenException:
                pass
        return marshalled_dict

    # obj is a non-string iterable, so marshal its members recursively
    # Zuul.marshal(set([o1, o2]))
    elif hasattr(obj, '__iter__'):
        marshalled_list = []
        for o in obj:
            try:
                marshalled_list.append(marshal(o, keys, marshallerName, objs))
            except AlreadySeenException:
                pass
        return marshalled_list
    elif isinstance(obj, DateTime ):
        return str(obj)
    # Nothing matched, so it's a string or number or other unmarshallable.
    else:
        return obj


def unmarshal(data, obj, unmarshallerName=''):
    """
    Set the values found the the data dictionary on the properties of the same
    name in obj.
    """
    unmarshaller = component.getAdapter(obj, IUnmarshaller, unmarshallerName)
    verify.verifyObject(IUnmarshaller, unmarshaller)
    # Get rid of immutable uid attribute
    if 'uid' in data:
        del data['uid']
    result = unmarshaller.unmarshal(data)
    notify(IndexingEvent(obj._object))    
    return result


def info(obj, adapterName=''):
    """
    Recursively adapt obj or members of obj to IInfo.
    """
    def infoize(o):
        return info(o, adapterName)

    if IInfo.providedBy(obj):
        return obj

    # obj is a dict, so apply to its values recursively
    elif isinstance(obj, dict):
        return dict((k, infoize(obj[k])) for k in obj)

    # obj is a non-string iterable, so apply to its members recursively
    elif hasattr(obj, '__iter__') and not isinstance(obj, ObjectManager):        
        return map(infoize, obj)
        

    # attempt to adapt; if no adapter, return obj itself
    else:
        return component.queryAdapter(obj, IInfo, adapterName, obj)


def filterUidsByPermission(dmd, permission, uids):
    """
    Returns a list of all the objects the currently logged in user has the passed
    in permission on. It also sends a browser message notifying the user
    of a failure if they dont have permission.

    @type  DMD: DataRoot
    @param DMD: you must pass in the dmd to this function to look up the objects
    @type  permission: string
    @param permission: Permission we are looking up
    @type  uids: List
    @param uids: List of object uids to check permission of
    @rtype:   List
    @return:  All the Uids the logged in user has the passed in permission on
    """
    validUids = []
    uids = (uids,) if isinstance(uids, basestring) else uids
    for uid in uids:
        obj = dmd.unrestrictedTraverse(uid)
        if checkPermission(permission, obj):
            validUids.append(uid)
        else:
            # send a message to the browser
            messaging.IMessageSender(obj).sendToBrowser(
                'Permission Error',
                "You do not have the %s permission on the object %s " % (permission, obj.titleOrId()),
                priority=messaging.WARNING)
    return validUids


def checkAdministeredObjectPermission(uid, permission, context=None):
    """
    Return True if the current user has the specified Administrated object
    permission on the given context or the dmd; otherwise, return False.
    """
    context = context or get_dmd()
    return checkPermission(permission, context.dmd.unrestrictedTraverse(uid))


def checkPermission(permission, context=None):
    """
    Return true if the current user has the specified permission on the given
    context or the dmd; otherwise, return false.
    """
    manager = AccessControl.getSecurityManager()
    context = context or get_dmd()
    return manager.checkPermission(permission, context)


def initialize(context):
    """Called by ZopeStartup to initialize product."""

    # ZEN-20490: The requests package logs what should be DEBUG information at
    # the INFO level. We'll only log >=WARNING for requests unless Zope has
    # been been configured for DEBUG logging.
    root_level = logging.getLogger().getEffectiveLevel()
    if root_level > logging.DEBUG:
        requests_logger = logging.getLogger('requests')
        requests_logger.setLevel(max(logging.WARNING, root_level))
