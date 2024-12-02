##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from zope.component import adapts
from Products.ZenUtils.jsonutils import json
from Products.Zuul.interfaces import IMarshallable
from Products.Zuul.interfaces import IMarshaller
from Products.Zuul.interfaces import IUnmarshaller
from Products.Zuul.interfaces import IInfo
from Products.Zuul.interfaces import ITreeNode

def getPublicProperties(obj):
    """
    Get all public __get__'ables like @property's.

    Note: This intentionally ignores regular properties and methods.
    """
    keys = [
        key for key in dir(obj)
            if not key.startswith('_') and not callable(getattr(obj, key))
    ]

    return keys

def _marshalImplicitly(obj):
    """
    Return a dictionary with all the attributes of obj except methods, and
    those that begin with '_'
    """
    data = {}
    for key in getPublicProperties(obj):
        value = getattr(obj, key)
        data[key] = value
    return data


def _marshalExplicitly(obj, keys):
    """
    Convert obj to a dict filtering the results based on a list of keys that
    is passed in.
    """
    data = {}
    for key in keys:
        try:
            value = getattr(obj, key)
        except AttributeError:
            pass
        else:
            if callable(value):
                value = value()
            data[key] = value
    return data


class Marshaller(object):
    """
    Uses a implicit mashalling if keys is None otherwise uses explicit
    marshalling.
    """
    implements(IMarshaller)
    adapts(IMarshallable)

    def __init__(self, obj):
        self._obj = obj

    def marshal(self, keys=None):
        if keys is None:
            data = _marshalImplicitly(self._obj)
        else:
            _keys = set(keys[:]) | set(self.getRequiredKeys())
            data = _marshalExplicitly(self._obj, _keys)
        return data

    def getRequiredKeys(self):
        return []


class InfoMarshaller(Marshaller):
    """
    Uses a implicit mashalling if keys is None otherwise uses explicit
    marshalling.
    """
    adapts(IInfo)

    def getRequiredKeys(self):
        # Ensure that uid makes it through
        return ['uid']


class TreeNodeMarshaller(object):
    """
    Converts a root tree node to a dictionary, recursively marshalling its
    children.
    """
    implements(IMarshaller)
    adapts(ITreeNode)

    def __init__(self, root):
        self.root = root

    def getKeys(self, node=None):
        node = node or self.root
        return getPublicProperties(node)

    def getValues(self, keys=None, node=None):
        node = node or self.root
        values = {}
        if keys is None:
            keys = self.getKeys(node)
        for attr in keys:
            val = getattr(node, attr)
            try:
                json(val)
            except TypeError:
                # We can't deal with it, just move on
                continue
            values[attr] = val
        return values

    def marshal(self, keys=None, node=None):
        node = node or self.root
        obj = self.getValues(keys, node)
        if node.leaf:
            obj['leaf'] = True
        else:
            obj['children'] = []
            for childNode in node.children:
                obj['children'].append(self.marshal(node=childNode))
        return obj


class DefaultUnmarshaller(object):
    """
    Sets all the values found in the data dictionary onto the obj object using
    the dictionary keys as the attribute names.  Raises an attribute error if
    any of the keys are not found on the object.
    """
    implements(IUnmarshaller)
    adapts(IInfo)

    def __init__(self, obj):
        self.obj = obj

    def unmarshal(self, data):
        for key, value in data.iteritems():
            try:
                setattr(self.obj, key, value)
            except AttributeError:                
                raise AttributeError("Property %s doesn't exist on %s" % (key, self.obj))
