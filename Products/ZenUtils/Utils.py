##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2018 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Utils

General utility functions module.

"""

from __future__ import absolute_import

import asyncore
import contextlib
import copy
import ctypes
import fcntl
import httplib
import logging
import math
import os
import popen2
import re
import select
import shlex
import socket
import string
import sys
import tempfile
import time
import types
import xmlrpclib

from decimal import Decimal
from functools import partial
from popen2 import Popen4
from itertools import chain
from subprocess import check_call, call, PIPE, STDOUT, Popen

from AccessControl import getSecurityManager, Unauthorized
from AccessControl.ZopeGuards import guarded_getattr
from Acquisition import aq_base, aq_inner, aq_parent
from decorator import decorator
from twisted.internet import task, reactor, defer
from zExceptions import NotFound
from ZODB.POSException import ConflictError
from zope.i18n import translate
from zope.interface import providedBy
from zope.schema._field import Password
from zope.schema import getFields
from ZServer.HTTPServer import zhttp_channel

from .Exceptions import ZenPathError, ZentinelException
from .jsonutils import unjson
from .Logger import (  # noqa: F401
    clearWebLoggingStream,
    HtmlFormatter,
    setLogLevel,
    setWebLoggingStream,
)
from .path import (  # noqa F401
    binPath,
    isZenBinFile,
    varPath,
    zenPath,
    zenpathjoin,
    zenpathsplit,
    zopePath,
)
from .Threading import (  # noqa: F401
    InterruptableThread,
    LineReader,
    ThreadInterrupt,
)

log = logging.getLogger("zen.Utils")
DEFAULT_SOCKET_TIMEOUT = 30


class DictAsObj(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)


def convToUnits(number=0, divby=1024.0, unitstr="B"):
    """Convert a number to its human-readable form. ie: 4GB, 4MB, etc.

    >>> convToUnits() # Don't do this!
    '0.0B'
    >>> convToUnits(None) # Don't do this!
    ''
    >>> convToUnits(123456789)
    '117.7MB'
    >>> convToUnits(123456789, 1000, "Hz")
    '123.5MHz'

    @param number: base number
    @type number: number
    @param divby: divisor to use to convert to appropriate prefix
    @type divby: number
    @param unitstr: base unit of the number
    @type unitstr: string
    @return: number with appropriate units
    @rtype: string
    """
    units = map(lambda x: x + unitstr, ("", "K", "M", "G", "T", "P"))
    try:
        numb = float(number)
    except Exception:
        return ""

    sign = 1
    if numb < 0:
        numb = abs(numb)
        sign = -1
    for unit in units:
        if numb < divby:
            break
        numb /= divby
    return "%.1f%s" % (numb * sign, unit)


def travAndColl(obj, toonerel, collect, collectname):
    """Walk a series of to one rels collecting collectname into collect.

    @param obj: object inside of Zope
    @type obj: object
    @param toonerel: a to-one relationship object
    @type toonerel: toonerel object
    @param collect: object list
    @type collect: list
    @param collectname: name inside of the to-one relation object
    @type collectname: string
    @return: list of objects
    @rtype: list
    """
    value = getattr(aq_base(obj), collectname, None)
    if value:
        collect.append(value)
    rel = getattr(aq_base(obj), toonerel, None)
    if callable(rel):
        nobj = rel()
        if nobj:
            return travAndColl(nobj, toonerel, collect, collectname)
    return collect


def getObjByPath(base, path, restricted=0):
    """Get a Zope object by its path (e.g. '/Devices/Server/Linux').

    Mostly a stripdown of unrestrictedTraverse method from Zope 2.8.8.
    @param base: base part of a path
    @type base: string
    @param path: path to an object inside of the DMD
    @type path: string
    @param restricted: flag indicated whether to use securityManager
    @type restricted: integer
    @return: object pointed to by the path
    @rtype: object
    """
    # MODIFY THIS FUNCTION WITH GREAT CARE.  A LOT OF CODE DEPENDS ON IT
    # BEHAVING AS IT DOES NOW.  BETTER YET, DON'T MODIFY IT.
    if not path:
        return base

    _getattr = getattr
    _none = None
    marker = object()

    if isinstance(path, str):
        # Unicode paths are not allowed
        path = path.split("/")
    else:
        path = list(path)

    REQUEST = {"TraversalRequestNameStack": path}
    path.reverse()
    path_pop = path.pop

    if len(path) > 1 and not path[0]:
        # Remove trailing slash
        path.pop(0)

    if restricted:
        securityManager = getSecurityManager()
    else:
        securityManager = _none

    if not path[-1]:
        # If the path starts with an empty string, go to the root first.
        path_pop()
        base = base.getPhysicalRoot()
        if restricted and not securityManager.validate(None, None, None, base):
            raise Unauthorized(base)

    obj = base
    while path:
        name = path_pop()

        if name[0] == "_":
            # Never allowed in a URL.
            raise NotFound(name)

        if name == "..":
            next = aq_parent(obj)
            if next is not _none:
                if restricted and not securityManager.validate(
                    obj, obj, name, next
                ):
                    raise Unauthorized(name)
                obj = next
                continue

        bobo_traverse = _getattr(obj, "__bobo_traverse__", _none)
        if bobo_traverse is not _none:
            next = bobo_traverse(REQUEST, name)
            if restricted:
                if aq_base(next) is not next:
                    # The object is wrapped, so the acquisition
                    # context is the container.
                    container = aq_parent(aq_inner(next))
                elif _getattr(next, "im_self", _none) is not _none:
                    # Bound method, the bound instance
                    # is the container
                    container = next.im_self
                elif _getattr(aq_base(obj), name, marker) == next:
                    # Unwrapped direct attribute of the object so
                    # object is the container
                    container = obj
                else:
                    # Can't determine container
                    container = _none
                try:
                    validated = securityManager.validate(
                        obj, container, name, next
                    )
                except Unauthorized:
                    # If next is a simple unwrapped property, it's
                    # parentage is indeterminate, but it may have been
                    # acquired safely.  In this case validate will
                    # raise an error, and we can explicitly check that
                    # our value was acquired safely.
                    validated = 0
                    if (
                        container is _none
                        and guarded_getattr(obj, name, marker) is next
                    ):
                        validated = 1
                if not validated:
                    raise Unauthorized(name)
        else:
            if restricted:
                next = guarded_getattr(obj, name, marker)
            else:
                next = _getattr(obj, name, marker)
            if next is marker:
                try:
                    next = obj[name]
                except AttributeError:
                    # Raise NotFound for easier debugging
                    # instead of AttributeError: __getitem__
                    raise NotFound(name)
                if restricted and not securityManager.validate(
                    obj, obj, _none, next
                ):
                    raise Unauthorized(name)
        obj = next
    return obj


def getObjByPath2(base, path, restricted=0):
    """Get a Zope object by its path (e.g. '/Devices/Server/Linux').

    Mostly a stripdown of unrestrictedTraverse method from Zope 2.8.8.

    @param base: base part of a path
    @type base: string
    @param path: path to an object inside of the DMD
    @type path: string
    @param restricted: flag indicated whether to use securityManager
    @type restricted: integer
    @return: object pointed to by the path
    @rtype: object
    """
    if not path:
        return base

    _getattr = getattr
    _none = None
    marker = object()

    if isinstance(path, str):
        # Unicode paths are not allowed
        path = path.split("/")
    else:
        path = list(path)

    REQUEST = {"TraversalRequestNameStack": path}
    path.reverse()
    path_pop = path.pop

    if len(path) > 1 and not path[0]:
        # Remove trailing slash
        path.pop(0)

    if restricted:
        securityManager = getSecurityManager()
    else:
        securityManager = _none

    if not path[-1]:
        # If the path starts with an empty string, go to the root first.
        path_pop()
        base = base.getPhysicalRoot()
        if restricted and not securityManager.validate(None, None, None, base):
            raise Unauthorized(base)

    obj = base
    while path:
        name = path_pop()

        if name[0] == "_":
            # Never allowed in a URL.
            raise NotFound(name)

        if name == "..":
            next = aq_parent(obj)
            if next is not _none:
                if restricted and not securityManager.validate(
                    obj, obj, name, next
                ):
                    raise Unauthorized(name)
                obj = next
                continue

        bobo_traverse = _getattr(obj, "__bobo_traverse__", _none)
        if bobo_traverse is not _none:
            next = bobo_traverse(REQUEST, name)
            if restricted:
                if aq_base(next) is not next:
                    # The object is wrapped, so the acquisition
                    # context is the container.
                    container = aq_parent(aq_inner(next))
                elif _getattr(next, "im_self", _none) is not _none:
                    # Bound method, the bound instance
                    # is the container
                    container = next.im_self
                elif _getattr(aq_base(obj), name, marker) == next:
                    # Unwrapped direct attribute of the object so
                    # object is the container
                    container = obj
                else:
                    # Can't determine container
                    container = _none
                try:
                    validated = securityManager.validate(
                        obj, container, name, next
                    )
                except Unauthorized:
                    # If next is a simple unwrapped property, it's
                    # parentage is indeterminate, but it may have been
                    # acquired safely.  In this case validate will
                    # raise an error, and we can explicitly check that
                    # our value was acquired safely.
                    validated = 0
                    if (
                        container is _none
                        and guarded_getattr(obj, name, marker) is next
                    ):
                        validated = 1
                if not validated:
                    raise Unauthorized(name)
        else:
            next = obj._getOb(name, None)
            if next is None:
                raise NotFound(name)
            if restricted and not securityManager.validate(
                obj, obj, _none, next
            ):
                raise Unauthorized(name)
        obj = next
    return obj


def capitalizeFirstLetter(s):
    # Don't use .title or .capitalize because they lower-case camel-cased names
    return s[0].capitalize() + s[1:] if s else s


RENAME_DISPLAY_TYPES = {
    "RRDTemplate": "Template",
    "ThresholdClass": "Threshold",
    "HoltWintersFailure": "Threshold",  # see Trac #29376
}


def getDisplayType(obj):
    """Get a printable string representing the type of this object."""
    # TODO: better implementation, like meta_display_type per class.
    typename = (
        str(getattr(obj, "meta_type", None) or obj.__class__.__name__)
        if obj
        else "None"
    )
    typename = capitalizeFirstLetter(typename)
    return RENAME_DISPLAY_TYPES.get(typename, typename)


def _getName(obj):
    return (
        getattr(obj, "getName", None)
        or getattr(obj, "name", None)
        or getattr(obj, "Name", None)
    )


def _getId(obj):
    return (
        getattr(obj, "getId", None)
        or getattr(obj, "id", None)
        or getattr(obj, "Id", None)
        or getattr(obj, "ID", None)
    )


def _getUid(obj):
    return (
        getattr(obj, "getPrimaryId", None)
        or getattr(obj, "uid", None)
        or getattr(obj, "Uid", None)
        or getattr(obj, "UID", None)
    )


def getDisplayName(obj):
    """Get a printable string representing the name of this object.

    Always returns something but it may not be pretty.
    """
    # TODO: better implementation, like getDisplayName() per class.
    name = (
        obj.titleOrId()
        if hasattr(obj, "titleOrId")
        else _getName(obj) or _getId(obj) or _getUid(obj)
    )
    if name is None:
        return str(obj)  # we tried our best
    return str(name() if callable(name) else name)


def getDisplayId(obj):
    """Get a printable string representing an ID of this object.

    Always returns something but it may not be pretty.
    """
    # TODO: better implementation, like getDisplayId() per class.
    dispId = _getUid(obj) or _getId(obj) or _getName(obj)
    if dispId is None:
        return str(obj)  # we tried our best
    return re.sub(
        r"^/zport/dmd", "", str(dispId() if callable(dispId) else dispId)
    )


def checkClass(myclass, className):
    """Perform issubclass using class name as string.

    @param myclass: generic object
    @type myclass: object
    @param className: name of a class
    @type className: string
    @return: the value 1 if found or None
    @rtype: integer or None
    """
    if myclass.__name__ == className:
        return 1
    for mycl in myclass.__bases__:
        if checkClass(mycl, className):
            return 1


def lookupClass(productName, classname=None):
    """Look in sys.modules for our class.

    @param productName: object in Products
    @type productName: string
    @param classname: class name
    @type classname: string
    @return: object at the classname in Products
    @rtype: object or None
    """
    if productName in sys.modules:
        mod = sys.modules[productName]

    elif "Products." + productName in sys.modules:
        mod = sys.modules["Products." + productName]

    else:
        return None

    if not classname:
        classname = productName.split(".")[-1]

    return getattr(mod, classname)


def importClass(modulePath, classname=""):
    """Import a class from the module given.

    @param modulePath: path to module in sys.modules
    @type modulePath: string
    @param classname: name of a class
    @type classname: string
    @return: the class in the module
    @rtype: class
    """
    try:
        if not classname:
            classname = modulePath.split(".")[-1]
        try:
            __import__(modulePath, globals(), locals(), classname)
            mod = sys.modules[modulePath]
        except (ValueError, ImportError, KeyError) as ex:
            raise ex

        return getattr(mod, classname)
    except AttributeError:
        raise ImportError(
            "Failed while importing class %s from module %s"
            % (classname, modulePath)
        )


def cleanstring(value):
    """Take the trailing \x00 off the end of a string.

    >>> txt = 'clean'
    >>> cleanstring(txt) == txt
    True
    >>> cleanstring(txt + chr(0)) == txt
    True
    >>> cleanstring(txt + chr(0) + chr(0)) == txt
    True

    @param value: sample string
    @type value: string
    @return: cleaned string
    @rtype: string
    """
    if isinstance(value, basestring):
        offset = value.find("\0")
        if offset >= 0:
            value = value[:offset]
    return value


def getSubObjects(base, filter=None, descend=None, retobjs=None):
    """
    Do a depth-first search looking for objects that the function filter
    returns as True. If descend is passed it will check to see if we
    should keep going down or not

    @param base: base object to start search
    @type base: object
    @param filter: filter to apply to each object to determine if it gets
        added to the returned list.
    @type filter: function or None
    @param descend: function to apply to each object to determine whether or
        not to continue searching.
    @type descend: function or None
    @param retobjs: list of objects found
    @type retobjs: list
    @return: list of objects found
    @rtype: list
    """
    if not retobjs:
        retobjs = []
    for obj in base.objectValues():
        if not filter or filter(obj):
            retobjs.append(obj)
        if not descend or descend(obj):
            retobjs = getSubObjects(obj, filter, descend, retobjs)
    return retobjs


def getSubObjectsMemo(base, filter=None, descend=None, memo={}):
    """
    Do a depth-first search looking for objects that the function filter
    returns as True. If descend is passed it will check to see if we
    should keep going down or not.

    This is a Python iterable.

    @param base: base object to start search
    @type base: object
    @param filter: filter to apply to each object to determine if it gets
        added to the returned list.
    @type filter: function or None
    @param descend: function to apply to each object to determine whether or
        not to continue searching.
    @type descend: function or None
    @param memo: dictionary of objects found (unused)
    @type memo: dictionary
    @return: list of objects found
    @rtype: list
    """
    from Products.ZenRelations.RelationshipManager import RelationshipManager

    if base.meta_type == "To One Relationship":
        objs = [base.obj]
    else:
        objs = base.objectValues()
    for obj in objs:
        if isinstance(
            obj, RelationshipManager
        ) and not obj.getPrimaryDmdId().startswith(base.getPrimaryDmdId()):
            continue
        if not filter or filter(obj):
            yield obj
        if not descend or descend(obj):
            for x in getSubObjectsMemo(obj, filter, descend, memo):
                yield x


def getAllConfmonObjects(base):
    """Get all ZenModelRM objects in database.

    @param base: base object to start searching
    @type base: object
    @return: list of objects
    @rtype: list
    """
    from Products.ZenModel.ZenModelRM import ZenModelRM
    from Products.ZenModel.ZenModelBase import ZenModelBase
    from Products.ZenRelations.ToManyContRelationship import (
        ToManyContRelationship,
    )
    from Products.ZenRelations.ToManyRelationship import ToManyRelationship
    from Products.ZenRelations.ToOneRelationship import ToOneRelationship

    def descend(obj):
        """Function to determine whether or not to continue searching.

        @param obj: object
        @type obj: object
        @return: True if we want to keep searching
        @rtype: boolean
        """
        return (
            isinstance(obj, ZenModelBase)
            or isinstance(obj, ToManyContRelationship)
            or isinstance(obj, ToManyRelationship)
            or isinstance(obj, ToOneRelationship)
        )

    def filter(obj):
        """
        Filter function to decide whether it's an object we
        want to know about or not.

        @param obj: object
        @type obj: object
        @return: True if we want to keep it
        @rtype: boolean
        """
        return isinstance(obj, ZenModelRM) and obj.id != "dmd"

    return getSubObjectsMemo(base, filter=filter, descend=descend)


def createHierarchyObj(root, name, factory, relpath="", llog=None):
    """
    Create a hierarchy object from its path we use relpath to skip down
    any missing relations in the path and factory is the constructor for
    this object.

    @param root: root from which to start
    @type root: object
    @param name: path to object
    @type name: string
    @param factory: factory object to create
    @type factory: factory object
    @param relpath: relationship within which we will recurse as objects are
        created, if any.
    @type relpath: object
    @param llog: unused
    @type llog: object
    @return: root object of a hierarchy
    @rtype: object
    """
    unused(llog)
    rootName = root.id
    for id in zenpathsplit(name):
        if id == rootName:
            continue
        if id == relpath or getattr(aq_base(root), relpath, False):
            root = getattr(root, relpath)
        if not getattr(aq_base(root), id, False):
            if id == relpath:
                raise AttributeError("relpath %s not found" % relpath)
            log.debug(
                "Creating object with id %s in object %s", id, root.getId()
            )
            newobj = factory(id)
            root._setObject(id, newobj)
        root = getattr(root, id)

    return root


def getHierarchyObj(root, name, relpath=None):
    """Return an object using its path relations are optional in the path.

    @param root: root from which to start
    @type root: object
    @param name: path to object
    @type name: string
    @param relpath: relationship within which we will recurse as objects are
        created, if any.
    @type relpath: object
    @return: root object of a hierarchy
    @rtype: object
    """
    for id in zenpathsplit(name):
        if id == relpath or getattr(aq_base(root), relpath, False):
            root = getattr(root, relpath)
        if not getattr(root, id, False):
            raise ZenPathError(
                "Path %s id %s not found on object %s"
                % (name, id, root.getPrimaryId())
            )
        root = getattr(root, id, None)

    return root


def basicAuthUrl(username, password, url):
    """
    Add the username and password to a url in the form
    http://username:password@host/path

    @param username: username
    @type username: string
    @param password: password
    @type password: string
    @param url: base URL to add username/password info
    @type url: string
    @return: URL with auth information incorporated
    @rtype: string
    """
    urlar = url.split("/")
    if not username or not password or urlar[2].find("@") > -1:
        return url
    urlar[2] = "%s:%s@%s" % (username, password, urlar[2])
    return "/".join(urlar)


def prepId(id, subchar="_"):
    r"""
    Make an id with valid url characters. Subs [^a-zA-Z0-9-_,.$\(\) ]
    with subchar.  If id then starts with subchar it is removed.

    @param id: user-supplied id
    @type id: string
    @return: valid id
    @rtype: string
    """
    _prepId = re.compile(r"[^a-zA-Z0-9-_,.$\(\) ]").sub
    _cleanend = re.compile(r"%s+$" % subchar).sub
    if id is None:
        raise ValueError("Ids can not be None")
    if not isinstance(id, basestring):
        id = str(id)
    id = _prepId(subchar, id)
    while id.startswith(subchar):
        if len(id) > 1:
            id = id[1:]
        else:
            id = "-"
    id = _cleanend("", id)
    id = id.lstrip(string.whitespace + "_").rstrip()
    return str(id)


def sendEmail(emsg, host, port=25, usetls=0, usr="", pwd=""):
    """
    Send an email.  Return a tuple:
    (sucess, message) where sucess is True or False.

    @param emsg: message to send
    @type emsg: email.MIMEText
    @param host: name of e-mail server
    @type host: string
    @param port: port number to communicate to the e-mail server
    @type port: integer
    @param usetls: boolean-type integer to specify whether to use TLS
    @type usetls: integer
    @param usr: username for TLS
    @type usr: string
    @param pwd: password for TLS
    @type pwd: string
    @return: (sucess, message) where sucess is True or False.
    @rtype: tuple
    """
    import smtplib

    fromaddr = emsg["From"]
    toaddr = map(lambda x: x.strip(), emsg["To"].split(","))
    try:
        server = smtplib.SMTP(host, port, timeout=DEFAULT_SOCKET_TIMEOUT)
        if usetls:
            server.ehlo()
            server.starttls()
            server.ehlo()
        if len(usr):
            server.login(usr, pwd)
        server.sendmail(fromaddr, toaddr, emsg.as_string())
        # Need to catch the quit because some servers using TLS throw an
        # EOF error on quit, so the email gets sent over and over
        try:
            server.quit()
        except Exception:
            pass
    except (smtplib.SMTPException, socket.error, socket.timeout):
        result = (False, "%s - %s" % tuple(sys.exc_info()[:2]))
    else:
        result = (True, "")
    return result


def sendPage(recipient, msg, pageCommand, deferred=False):
    """
    Send a page.  Return a tuple: (success, message) where
    sucess is True or False.

    @param recipient: name to where a page should be sent
    @type recipient: string
    @param msg: message to send
    @type msg: string
    @param pageCommand: command that will send a page
    @type pageCommand: string
    @return: (sucess, message) where sucess is True or False.
    @rtype: tuple
    """
    import subprocess

    env = dict(os.environ)
    env["RECIPIENT"] = recipient
    msg = str(msg)
    p = subprocess.Popen(
        pageCommand,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
        env=env,
    )
    p.stdin.write(msg)
    p.stdin.close()
    response = p.stdout.read()
    return (not p.wait(), response)


def zdecode(context, value):
    """Convert a string using the decoding found in zCollectorDecoding.

    @param context: Zope object
    @type context: object
    @param value: input string
    @type value: string
    @return: converted string
    @rtype: string
    """
    if isinstance(value, str):
        decoding = getattr(context, "zCollectorDecoding", "utf-8")
        value = value.decode(decoding)
    return value


def localIpCheck(context, ip):
    """Test to see if an IP should not be included in the network map.

    Uses the zLocalIpAddresses to decide.

    @param context: Zope object
    @type context: object
    @param ip: IP address
    @type ip: string
    @return: regular expression match or None (if not found)
    @rtype: re match object
    """
    return re.search(getattr(context, "zLocalIpAddresses", "^$"), ip)


def localInterfaceCheck(context, intname):
    """Test to see if an interface should not be included in the network map.

    Uses the zLocalInterfaceNames to decide.

    @param context: Zope object
    @type context: object
    @param intname: network interface name
    @type intname: string
    @return: regular expression match or None (if not found)
    @rtype: re match object
    """
    return re.search(getattr(context, "zLocalInterfaceNames", "^$"), intname)


def cmpClassNames(obj, classnames):
    """
    Check to see if any of an object's base classes are in a list of class
    names. Like isinstance(), but without requiring a class to compare against.

    @param obj: object
    @type obj: object
    @param classnames: class names
    @type classnames: list of strings
    @return: result of the comparison
    @rtype: boolean
    """
    finalnames = set()
    x = [obj.__class__]
    while x:
        thisclass = x.pop()
        x.extend(thisclass.__bases__)
        finalnames.add(thisclass.__name__)
    return bool(set(classnames).intersection(finalnames))


def resequence(context, objects, seqmap, origseq, REQUEST):
    """Resequence a seqmap.

    @param context: Zope object
    @type context: object
    @param objects: objects
    @type objects: list
    @param seqmap: sequence map
    @type seqmap: list
    @param origseq: sequence map
    @type origseq: list
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return:
    @rtype: string
    """
    if seqmap and origseq:
        try:
            origseq = tuple(long(s) for s in origseq)
            seqmap = tuple(float(s) for s in seqmap)
        except ValueError:
            origseq = ()
            seqmap = ()
        orig = dict((o.sequence, o) for o in objects)
        if origseq:
            for oldSeq, newSeq in zip(origseq, seqmap):
                orig[oldSeq].sequence = newSeq
    for i, obj in enumerate(sorted(objects, key=lambda a: a.sequence)):
        obj.sequence = i

    if REQUEST:
        return context.callZenScreen(REQUEST)


def cleanupSkins(dmd):
    """Prune out objects.

    @param dmd: Device Management Database
    @type dmd: DMD object
    """
    ps = dmd.getPhysicalRoot().zport.portal_skins
    layers = ps._objects
    layers = filter(lambda x: getattr(ps, x["id"], False), layers)
    ps._objects = tuple(layers)


def edgesToXML(edges, start=()):
    """Convert edges to an XML file.

    @param edges: edges
    @type edges: list
    @return: XML-formatted string
    @rtype: string
    """
    nodet = '<Node id="%s" prop="%s" icon="%s" color="%s"/>'
    edget = '<Edge fromID="%s" toID="%s"/>'
    xmlels = ['<Start name="%s" url="%s"/>' % start]
    nodeels = []
    edgeels = []
    for node_a, node_b in edges:
        a_title, a_icon_path, a_color, a_id = node_a
        b_title, b_icon_path, b_color, b_id = node_b
        node1 = nodet % (a_id, a_title, a_icon_path, a_color)
        node2 = nodet % (b_id, b_title, b_icon_path, b_color)
        edge1 = edget % (a_title, b_id)
        if node1 not in nodeels:
            nodeels.append(node1)
        if node2 not in nodeels:
            nodeels.append(node2)
        if edge1 not in edgeels:
            edgeels.append(edge1)

    xmlels.extend(nodeels)
    xmlels.extend(edgeels)
    xmldoc = "<graph>%s</graph>" % "".join(list(xmlels))

    return xmldoc


def extractPostContent(REQUEST):
    """
    IE puts the POST content in one place in the REQUEST object, and Firefox in
    another. Thus we need to try both.

    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: POST content
    @rtype: string
    """
    try:
        # Firefox
        return REQUEST._file.read()
    except Exception:
        try:
            # IE
            return REQUEST.form.keys()[0]
        except Exception:
            return ""


def unused(*args):
    """A no-op function useful for shutting up pychecker.

    @param *args: arbitrary arguments
    @type *args: objects
    @return: count of the objects
    @rtype: integer
    """
    pass


def isXmlRpc(REQUEST):
    """Did we receive a XML-RPC call?

    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: True if REQUEST is an XML-RPC call
    @rtype: boolean
    """
    if REQUEST and REQUEST["CONTENT_TYPE"].find("xml") > -1:
        return True
    else:
        return False


def setupLoggingHeader(context, REQUEST):
    """Extract out the 2nd outermost table.

    @param context: Zope object
    @type context: Zope object
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: response
    @rtype: string
    """
    response = REQUEST.RESPONSE
    dlh = context.discoverLoggingHeader()
    idx = dlh.rindex("</table>")
    dlh = dlh[:idx]
    idx = dlh.rindex("</table>")
    dlh = dlh[:idx]
    response.write(str(dlh[:idx]))

    return setWebLoggingStream(response)


def executeCommand(cmd, REQUEST, write=None):
    """Execute the command and return the output.

    @param cmd: command to execute
    @type cmd: string
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: result of executing the command
    @rtype: string
    """
    xmlrpc = isXmlRpc(REQUEST)
    result = 0
    try:
        if REQUEST:
            response = REQUEST.RESPONSE
        else:
            response = sys.stdout
        if write is None:

            def _write(s):
                response.write(s)
                response.flush()

            write = _write
        log.info("Executing command: %s", " ".join(cmd))
        f = Popen4(cmd)
        while 1:
            s = f.fromchild.readline()
            if not s:
                break
            elif write:
                write(s)
            else:
                log.info(s)
    except ZentinelException as e:
        if xmlrpc:
            return 1
        log.critical(e)
    except Exception:
        if xmlrpc:
            return 1
        raise
    else:
        result = f.wait()
        result = int(hex(result)[:-2], 16)
    return result


def ipsort(a, b):
    """Compare (cmp()) a + b's IP addresses.

    These addresses may contain subnet mask info.

    @param a: IP address
    @type a: string
    @param b: IP address
    @type b: string
    @return: result of cmp(a.ip,b.ip)
    @rtype: boolean
    """
    # Use 0.0.0.0 instead of blank string
    if not a:
        a = "0.0.0.0"
    if not b:
        b = "0.0.0.0"

    # Strip off netmasks
    a, b = map(lambda x: x.rsplit("/")[0], (a, b))
    return cmp(*map(socket.inet_aton, (a, b)))


def ipsortKey(a):
    """Key function to replace cmp version of ipsort.

    @param a: IP address
    @type a: string
    @return: result of socket.inet_aton(a.ip)
    @rtype: int
    """
    if not a:
        a = "0.0.0.0"
    a = a.rsplit("/")[0]
    return socket.inet_aton(a)


def unsigned(v):
    """Convert negative 32-bit values into the 2's complement unsigned value.

    >>> str(unsigned(-1))
    '4294967295'
    >>> unsigned(1)
    1L
    >>> unsigned(1e6)
    1000000L
    >>> unsigned(1e10)
    10000000000L

    @param v: number
    @type v: negative 32-bit number
    @return: 2's complement unsigned value
    @rtype: unsigned int
    """
    v = long(v)
    if v < 0:
        return int(ctypes.c_uint32(v).value)
    return v


def nanToNone(value):
    try:
        if math.isnan(value):
            return None
    except TypeError:
        pass
    return value


def executeStreamCommand(cmd, writefunc, timeout=30):
    """Execute cmd in the shell and send the output to writefunc.

    @param cmd: command to execute
    @type cmd: string
    @param writefunc: output function
    @type writefunc: function
    @param timeout: maxium number of seconds to wait for the command to execute
    @type timeout: number
    """
    child = popen2.Popen4(shlex.split(cmd))
    flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
    fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
    pollPeriod = 1
    endtime = time.time() + timeout
    firstPass = True
    while time.time() < endtime and (firstPass or child.poll() == -1):
        firstPass = False
        r, w, e = select.select([child.fromchild], [], [], pollPeriod)
        if r:
            t = child.fromchild.read()
            if t:
                writefunc(t)
    if child.poll() == -1:
        writefunc("Command timed out")
        import signal

        os.kill(child.pid, signal.SIGKILL)


def monkeypatch(target):
    """A decorator to patch the decorated function into the given class.

    >>> @monkeypatch('Products.ZenModel.DataRoot.DataRoot')
    ... def do_nothing_at_all(self):
    ...     print "I do nothing at all."
    ...
    >>> from Products.ZenModel.DataRoot import DataRoot
    >>> hasattr(DataRoot, 'do_nothing_at_all')
    True
    >>> DataRoot('dummy').do_nothing_at_all()
    I do nothing at all.

    You can also call the original within the new method
    using a special variable available only locally.

    >>> @monkeypatch('Products.ZenModel.DataRoot.DataRoot')
    ... def getProductName(self):
    ...     print "Doing something additional."
    ...     return 'core' or original(self)
    ...
    >>> from Products.ZenModel.DataRoot import DataRoot
    >>> DataRoot('dummy').getProductName()
    Doing something additional.
    'core'

    You can also stack monkeypatches.

        ### @monkeypatch('Products.ZenModel.System.System')
        ... @monkeypatch('Products.ZenModel.DeviceGroup.DeviceGroup')
        ... @monkeypatch('Products.ZenModel.Location.Location')
        ... def foo(self):
        ...     print "bar!"
        ...
        ### dmd.Systems.foo()
        bar!
        ### dmd.Groups.foo()
        bar!
        ### dmd.Locations.foo()
        bar!

    @param target: class
    @type target: class object
    @return: decorator function return
    @rtype: function
    """
    if isinstance(target, basestring):
        mod, klass = target.rsplit(".", 1)
        target = importClass(mod, klass)

    def patcher(func):
        original = getattr(target, func.__name__, None)
        if original is None:
            setattr(target, func.__name__, func)
            return func

        new_globals = copy.copy(func.func_globals)
        new_globals["original"] = original
        new_func = types.FunctionType(
            func.func_code,
            globals=new_globals,
            name=func.func_name,
            argdefs=func.func_defaults,
            closure=func.func_closure,
        )
        setattr(target, func.__name__, new_func)
        return func

    return patcher


def nocache(f):
    """Decorator to set headers which force browser to not cache request.

    This is intended to decorate methods of BrowserViews.

    @param f: class
    @type f: class object
    @return: decorator function return
    @rtype: function
    """

    def inner(self, *args, **kwargs):
        """Inner portion of the decorator.

        @param *args: arguments
        @type *args: possible list
        @param **kwargs: keyword arguments
        @type **kwargs: possible list
        @return: decorator function return
        @rtype: function
        """
        self.request.response.setHeader(
            "Cache-Control", "no-cache, must-revalidate"
        )
        self.request.response.setHeader("Pragma", "no-cache")
        self.request.response.setHeader(
            "Expires", "Sat, 13 May 2006 18:02:00 GMT"
        )
        # Get rid of kw used to prevent browser caching
        kwargs.pop("_dc", None)
        return f(self, *args, **kwargs)

    return inner


def formreq(f):
    """Decorator to pass in request.form information as arguments to a method.

    These are intended to decorate methods of BrowserViews.

    @param f: class
    @type f: class object
    @return: decorator function return
    @rtype: function
    """

    def inner(self, *args, **kwargs):
        """Inner portion of the decorator.

        @param *args: arguments
        @type *args: possible list
        @param **kwargs: keyword arguments
        @type **kwargs: possible list
        @return: decorator function return
        @rtype: function
        """
        if self.request.REQUEST_METHOD == "POST":
            content = extractPostContent(self.request)
            try:
                args += (unjson(content),)
            except ValueError:
                kwargs.update(self.request.form)
        else:
            kwargs.update(self.request.form)
        # Get rid of useless Zope thing that appears when no querystring
        kwargs.pop("-C", None)
        # Get rid of kw used to prevent browser caching
        kwargs.pop("_dc", None)
        return f(self, *args, **kwargs)

    return inner


class Singleton(type):
    """
    Metaclass that ensures only a single instance of a class is ever created.

    This is accomplished by storing the first instance created as an attribute
    of the class itself, then checking that attribute for later constructor
    calls.
    """

    def __init__(cls, *args, **kwargs):
        super(Singleton, cls).__init__(*args, **kwargs)
        cls._singleton_instance = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton_instance is None:
            cls._singleton_instance = super(Singleton, cls).__call__(
                *args, **kwargs
            )
        return cls._singleton_instance


def readable_time(seconds, precision=1):
    """Convert some number of seconds into a human-readable string.

    @param seconds: The number of seconds to convert
    @type seconds: int
    @param precision: The maximum number of time units to include.
    @type precision: int
    @rtype: str

    >>> readable_time(None)
    '0 seconds'
    >>> readable_time(0)
    '0 seconds'
    >>> readable_time(0.12)
    '0 seconds'
    >>> readable_time(1)
    '1 second'
    >>> readable_time(1.5)
    '1 second'
    >>> readable_time(60)
    '1 minute'
    >>> readable_time(60*60*3+12)
    '3 hours'
    >>> readable_time(60*60*3+12, 2)
    '3 hours 12 seconds'
    """
    if seconds is None:
        return "0 seconds"
    remaining = abs(seconds)
    if remaining < 1:
        return "0 seconds"

    names = ("year", "month", "week", "day", "hour", "minute", "second")
    mults = (
        60 * 60 * 24 * 365,
        60 * 60 * 24 * 30,
        60 * 60 * 24 * 7,
        60 * 60 * 24,
        60 * 60,
        60,
        1,
    )
    result = []
    for name, div in zip(names, mults):
        num = Decimal(str(math.floor(remaining / div)))
        remaining -= int(num) * div
        num = int(num)
        if num:
            result.append("%d %s%s" % (num, name, num > 1 and "s" or ""))
        if len(result) == precision:
            break
    return " ".join(result)


def relative_time(t, precision=1, cmptime=None):
    """
    Return a human-readable string describing time relative to C{cmptime}
    (defaulted to now).

    @param t: The time to convert, in seconds since the epoch.
    @type t: int
    @param precision: The maximum number of time units to include.
    @type t: int
    @param cmptime: The time from which to compute the difference, in seconds
    since the epoch
    @type cmptime: int
    @rtype: str

    >>> relative_time(time.time() - 60*10)
    '10 minutes ago'
    >>> relative_time(time.time() - 60*10-3, precision=2)
    '10 minutes 3 seconds ago'
    >>> relative_time(time.time() - 60*60*24*10, precision=2)
    '1 week 3 days ago'
    >>> relative_time(time.time() - 60*60*24*365-1, precision=2)
    '1 year 1 second ago'
    >>> relative_time(time.time() + 1 + 60*60*24*7*2) # Add 1 for rounding
    'in 2 weeks'
    """
    if cmptime is None:
        cmptime = time.time()
    seconds = Decimal(str(t - cmptime))
    result = readable_time(seconds, precision)
    if seconds < 0:
        result += " ago"
    else:
        result = "in " + result
    return result


def is_browser_connection_open(request):
    """Check to see if the TCP connection to the browser is still open.

    This might be used to interrupt an infinite while loop, which would
    preclude the thread from being destroyed even though the connection has
    been closed.
    """
    missing = object()
    env = getattr(request, "environ", {})
    creation_time = env.get("channel.creation_time", missing)
    if creation_time is missing:
        return False
    return any(
        getattr(cnxn, "creation_time", missing) == creation_time
        for cnxn in asyncore.socket_map.values()
        if isinstance(cnxn, zhttp_channel)
    )


EXIT_CODE_MAPPING = {
    0: "Success",
    1: "General error",
    2: "Misuse of shell builtins",
    126: (
        "Command invoked cannot execute, permissions problem or command "
        "is not an executable"
    ),
    127: "Command not found",
    128: (
        "Invalid argument to exit, exit takes only integers in the "
        "range 0-255"
    ),
    130: "Fatal error signal: 2, Command terminated by Control-C",
}


def getExitMessage(exitCode):
    """
    Return a nice exit message that corresponds to the given exit status code

    @param exitCode: process exit code
    @type exitCode: integer
    @return: human-readable version of the exit code
    @rtype: string
    """
    if exitCode in EXIT_CODE_MAPPING.keys():
        return EXIT_CODE_MAPPING[exitCode]
    elif exitCode >= 255:
        return (
            "Exit status out of range, exit takes only integer arguments "
            "in the range 0-255"
        )
    elif exitCode > 128:
        return "Fatal error signal: %s" % (exitCode - 128)
    return "Unknown error code: %s" % exitCode


def set_context(ob):
    """Wrap an object in a REQUEST context."""
    from ZPublisher.HTTPRequest import HTTPRequest
    from ZPublisher.HTTPResponse import HTTPResponse
    from ZPublisher.BaseRequest import RequestContainer

    resp = HTTPResponse(stdout=None)
    env = {
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "REQUEST_METHOD": "GET",
    }
    req = HTTPRequest(None, env, resp)
    return ob.__of__(RequestContainer(REQUEST=req))


def dumpCallbacks(deferred):
    """Dump the callback chain of a Twisted Deferred object.

    The chain will be displayed on standard output.

    @param deferred: the twisted Deferred object to dump
    @type deferred: a Deferred object
    """
    callbacks = deferred.callbacks
    print "%-39s %-39s" % ("Callbacks", "Errbacks")
    print "%-39s %-39s" % ("-" * 39, "-" * 39)
    for cbs in callbacks:
        callback = cbs[0][0]
        callbackName = "%s.%s" % (callback.__module__, callback.func_name)
        errback = cbs[1][0]
        errbackName = "%s.%s" % (errback.__module__, errback.func_name)
        print "%-39.39s %-39.39s" % (callbackName, errbackName)


def LazyMap__iter__(self):
    for i in range(len(self._seq)):
        try:
            brain = self[i]
            yield brain
        except (NotFound, KeyError, AttributeError):
            if log:
                log.warn("Stale record in catalog: (key) %s", self._seq[i])
        except IndexError:
            break


def _monkeypath_LazyMap__iter__():
    # Add __iter__ method to LazyMap (used to implement catalog queries) to
    # handle errors while iterating over the query results using __getitem__.
    from Products.ZCatalog.Lazy import LazyMap

    LazyMap.__iter__ = LazyMap__iter__


_monkeypath_LazyMap__iter__()


def getObjectsFromCatalog(catalog, query=None, log=None):
    """
    Generator that can be used to load all objects of out a catalog and skip
    any objects that are no longer able to be loaded.
    """
    for brain in catalog(query):
        try:
            ob = brain.getObject()
            yield ob
        except (NotFound, KeyError, AttributeError):
            if log:
                log.warn("Stale %s record: %s", catalog.id, brain.getPath())


def getObjectsFromModelCatalog(catalog, query=None, log=None):
    """
    Generator that can be used to load objects out model catalog and skip
    any objects that are no longer able to be loaded.
    """
    for brain in catalog.search(query=query):
        try:
            ob = brain.getObject()
            if ob:
                yield ob
        except (NotFound, KeyError, AttributeError):
            ob = None
        if ob is None and log:
            log.warn("Stale record in Model Catalog: %s", brain.getPath())


_LOADED_CONFIGS = set()


def load_config(file, package=None, execute=True):
    """Load a ZCML file into the context (and avoids duplicate imports)."""
    global _LOADED_CONFIGS
    key = (file, package)
    if key not in _LOADED_CONFIGS:
        from Zope2.App import zcml

        zcml.load_config(file, package, execute)
        _LOADED_CONFIGS.add(key)


def load_config_override(file, package=None, execute=True):
    """Load an additional ZCML file into the context, overriding others.

    Use with extreme care.
    """
    global _LOADED_CONFIGS
    key = (file, package)
    if key not in _LOADED_CONFIGS:
        from zope.configuration import xmlconfig
        from Zope2.App.zcml import _context

        xmlconfig.includeOverrides(_context, file, package=package)
        if execute:
            _context.execute_actions()
        _LOADED_CONFIGS.add(key)


def has_feature(name):
    """Return True if named feature is provided, otherwise return False."""
    from Zope2.App.zcml import _context

    return _context.hasFeature(name)


def rrd_daemon_running():
    """The RRD methods in this module are deprecated."""


def rrd_daemon_args():
    """The RRD methods in this module are deprecated."""


def rrd_daemon_reset():
    """The RRD methods in this module are deprecated."""


def rrd_daemon_retry(fn):
    """The RRD methods in this module are deprecated."""


@contextlib.contextmanager
def get_temp_dir():
    import shutil

    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)


def getDefaultZopeUrl():
    """Returns the default Zope URL."""
    return "http://localhost:8080"


def swallowExceptions(log, msg=None, showTraceback=True, returnValue=None):
    """USE THIS CAUTIOUSLY. Don't hide exceptions carelessly.

    Decorator to safely call a method, logging exceptions without raising them.

    Example:
        @swallowExceptions(myLogger, 'Error while closing files')
        def closeFilesBeforeExit():
            ...

    @param log           Which logger to use, or None to not log.
    @param msg           The error message.
    @param showTraceback True to include the stacktrace (the default).
    @param returnValue   The return value on error.
    """

    @decorator
    def callSafely(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConflictError:
            raise
        except Exception as e:
            if log is not None:
                if showTraceback:
                    log.exception(msg if msg else str(e))
                else:
                    log.warn(msg if msg else str(e))
            return returnValue

    return callSafely


def getAllParserOptionsGen(parser):
    """Returns a generator of all valid options for the optparse.OptionParser.

    @param parser The parser to retrieve options for.
    @type parser  optparse.OptionParser
    @return       A generator returning all options for the parser.
    @rtype        generator of optparse.Option
    """
    for optContainer in chain((parser,), parser.option_groups):
        for option in optContainer.option_list:
            yield option


def ipv6_available():
    try:
        socket.socket(socket.AF_INET6).close()
        return True
    except socket.error:
        return False


def atomicWrite(filename, data, raiseException=True, createDir=False):
    """Atomically writes data to filename.

    @param filename Complete path of file to write to.
    @type filename string
    @param data Data to write to destination file.
    @type data writeable object (eg, string)
    @param raiseException Raise errors that occur during atomicWrite
    @type raiseException bool
    @param createDir Create the destination directory if it does not exists.
    @type createDir bool
    @rtype a suppressed exception, if any
    """
    dirName = os.path.dirname(filename)
    if createDir and not os.path.exists(dirName):
        os.makedirs(dirName)
    tfile = None
    ex = None
    try:
        # create a file in the same directory as the destination file
        with tempfile.NamedTemporaryFile(dir=dirName, delete=False) as tfile:
            tfile.write(data)
        os.rename(tfile.name, filename)  # atomic operation on POSIX systems
    except Exception as ex:
        if tfile is not None and os.path.exists(tfile.name):
            try:
                os.remove(tfile.name)
            except Exception:
                pass
        if raiseException:
            raise ex
    return ex


def isRunning(daemon):
    """Return True if the specified daemon is running."""
    return call([daemon, "status"], stdout=PIPE, stderr=STDOUT) == 0


def requiresDaemonShutdown(daemon, logger=log):
    """Performs an operation while the requested daemon is not running.

    Will stop and restart the daemon automatically.

    Throws a CalledProcessError if either shutdown or restart fails.

    @param daemon        Which daemon to bring down for the operation.
    @param logger        Which logger to use, or None to not log.
    """

    @decorator
    def callWithShutdown(func, *args, **kwargs):
        cmd = binPath(daemon)
        running = isRunning(cmd)
        if running:
            if logger:
                logger.info(
                    "Shutting down %s for %s operation...",
                    daemon,
                    func.__name__,
                )
            check_call([cmd, "stop"])

            # make sure the daemon is actually shut down
            for i in range(30):
                nowrunning = isRunning(cmd)
                if not nowrunning:
                    break
                time.sleep(1)
            else:
                raise Exception(
                    "Failed to terminate daemon %s with command %s"
                    % (daemon, cmd + " stop")
                )

        try:
            return func(*args, **kwargs)

        except Exception as ex:
            if logger:
                logger.error(
                    "Error performing %s operation: %s", func.__name__, ex
                )
            raise

        finally:
            if running:
                if logger:
                    logger.info(
                        "Starting %s after %s operation...",
                        daemon,
                        func.__name__,
                    )
                check_call([cmd, "start"])

    return callWithShutdown


def wait(seconds):
    """Delays execution of subsequent code.

    Example:

        @defer.inlineCallbacks
        def incrOne(a):
            b = a + 1
            yield wait(5)
            defer.returnValue(a)

    In function incrOne, the 'yield wait(5)' introduces a five second
    pause between 'b = a + 1' and 'defer.returnValue(a)'.

    This function should be used a replacement for time.sleep() in
    (twisted) asynchronous code.

    @param seconds {float,int,long} Number of seconds to pause before
        allowing execution to continue.
    """
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, seconds)
    return d


giveTimeToReactor = partial(task.deferLater, reactor, 0)


def addXmlServerTimeout(server, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    """
    Given an instance of xmlrpclib.ServerProxy (same as xmlrpclib.Server),
    attach a timeout for the underlying http/socket connection.

    Example use:
        server = xmlrpclib.ServerProxy((host,port))
        addXmlServerTimeout( server, 5 )
        server.myCall(param1)

    @param server: the xmlrpc server proxy
    @type server: xmlrpclib.ServerProxy
    @param timeout: timeout in seconds
    @type timeout: float

    """

    """
    This method contains code copied from xmlrpclib.py from the standard
    Python 2.7 distribution. Please see that file for usage permissions
    and disclaimers.

    # Copyright (c) 1999-2002 by Secret Labs AB
    # Copyright (c) 1999-2002 by Fredrik Lundh
    """

    def _timeout_make_connection(self, host):
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        chost, self._extra_headers, x509 = self.get_host_info(host)
        self._connection = host, httplib.HTTPConnection(chost, timeout=timeout)
        return self._connection[1]

    def _timeout_make_safe_connection(self, host):
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        try:
            HTTPS = httplib.HTTPSConnection
        except AttributeError:
            raise NotImplementedError(
                "your version of httplib doesn't support HTTPS"
            )
        else:
            chost, self._extra_headers, x509 = self.get_host_info(host)
            kwargs = dict(timeout=timeout)
            if x509:
                kwargs.update(x509)
            self._connection = host, HTTPS(chost, None, **kwargs)
            return self._connection[1]

    transport = server._ServerProxy__transport
    if isinstance(transport, xmlrpclib.SafeTransport):
        transport.make_connection = types.MethodType(
            _timeout_make_safe_connection, transport
        )
    else:
        transport.make_connection = types.MethodType(
            _timeout_make_connection, transport
        )

    return server


def snmptranslate(*args):
    command = " ".join(["snmptranslate", "-Ln"] + list(args))
    proc = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    output, errors = proc.communicate()
    proc.wait()
    if proc.returncode != 0:
        log.error(
            "snmptranslate returned errors for %s: %s", list(args), errors
        )
        return "Error translating: %s" % list(args)

    return output.strip()


def getTranslation(msgId, REQUEST, domain="zenoss"):
    """
    Take a string like:
       'en-us,en;q=0.7,ja;q=0.3'

    and choose the best translation, if any.

    Assumes that the input msgId is
    """
    langs = REQUEST.get("HTTP_ACCEPT_LANGUAGE").split(",")
    langOrder = []
    for lang in langs:
        data = lang.split(";q=")
        if len(data) == 1:
            langOrder.append((1.0, lang))
        else:
            langOrder.append((data[1], data[0]))
    # Search for translations
    for weight, lang in sorted(langOrder):
        msg = translate(msgId, domain=domain, target_language=lang)
        # Relies on Zenoss currently using the text as the msgId
        if msg != msgId:
            return msg
    return msg


def unpublished(func):
    """Makes decorated method unpublished.

    Removes docstring of decorated method thus it will not be
    published by Zope.
    """
    func.__doc__ = None
    return func


def executeSshCommand(device, cmd, writefunc):
    from Products.DataCollector.SshClient import SshClient

    ssh_client_options = DictAsObj(
        loginTries=device.zCommandLoginTries,
        searchPath=device.zCommandSearchPath,
        existenceTest=device.zCommandExistanceTest,
        username=device.zCommandUsername,
        password=device.zCommandPassword,
        loginTimeout=device.zCommandLoginTimeout,
        commandTimeout=device.zCommandCommandTimeout,
        keyPath=device.zKeyPath,
        concurrentSessions=device.zSshConcurrentSessions,
    )
    connection = SshClient(
        device,
        device.manageIp,
        device.zCommandPort,
        options=ssh_client_options,
    )
    connection.clientFinished = reactor.stop
    connection.workList.append(cmd)
    connection._commands.append(cmd)
    connection.run()
    reactor.run()
    # getResults() normally returns [(None, "command output")],
    # or [(None,'')] in case of empty output,
    # or [] when cmd was not executed in some reasons (e.g. wrong path)
    for x in connection.getResults():
        [writefunc(y) for y in x if y]


def escapeSpecChars(value):
    escape_re = re.compile(r"(?<!\\)(?P<char>[$&|+\-!(){}[\]^~*?:])")
    return escape_re.sub(r"\\\g<char>", value)


def getQueryArgsFromRequest(request):
    """Returns a map of query args created from a zope HTTPRequest object."""
    query_args = {}
    for arg in request.QUERY_STRING.split("&"):
        parts = arg.split("=", 1)
        if len(parts) == 2:
            query_args[parts[0]] = parts[1]
        elif len(parts) == 1 and parts[0]:
            query_args[parts[0]] = True
    return query_args


def getPasswordFields(interface):
    passwordFields = set()
    for iface in providedBy(interface):
        fields = getFields(iface)
        if not fields:
            continue
        for key, value in fields.iteritems():
            if isinstance(value, Password):
                passwordFields.add(key)
    return passwordFields


def maskSecureProperties(data, secure_properties=[]):
    for prop in secure_properties:
        if data.get(prop, None):
            data.update({prop: "*" * len(data[prop])})
    return data
