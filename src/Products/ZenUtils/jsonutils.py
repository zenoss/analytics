##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import json as _json
import re
from array import array

def _recursiveCaster(ob):
    if isinstance(ob, dict):
        result = {}
        for k, v in ob.iteritems():
            result[str(k)] = _recursiveCaster(v)
        return result
    elif isinstance(ob, list):
        return [_recursiveCaster(x) for x in ob]
    elif isinstance(ob, unicode):
        return str(ob)
    else:
        return ob


class StringifyingDecoder(_json.JSONDecoder):
    """
    Casts all unicode objects as strings. This is necessary until Zope is less
    stupid.
    """
    def decode(self, s):
        result = super(StringifyingDecoder, self).decode(s)
        return _recursiveCaster(result)

class JavaScript(object):
    """A simple class that represents a JavaScript literal that should not be JSON encoded."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class JavaScriptRegex(JavaScript):
    """A simple class that represents a JavaScript Regex literal that should not be JSON encoded."""
    def __str__(self):
        return '/' + self.value + '/'

class ObjectEncoder(_json.JSONEncoder):
    _array_converters = { 'c':array.tostring,
                          'u':array.tounicode,
                        }
    def default(self, obj):
        if hasattr(obj, '__json__') and callable(obj.__json__):
            return obj.__json__()
        if isinstance(obj, array):
            return self._array_converters.get(obj.typecode, array.tolist)(obj)
        return super(ObjectEncoder,self).default(obj)

class JavaScriptEncoder(ObjectEncoder):
    """A JavaScript encoder based on JSON. It encodes like normal JSON except it passes JavaScript objects un-encoded."""

    _js_start = '__js_start__'
    _js_end = '__js_end__'
    _js_re = re.compile(r'\["%s", (.*?), "%s"\]' % (_js_start, _js_end))

    def default(self, obj):
        if isinstance(obj, JavaScript):
            return [self._js_start, str(obj), self._js_end]

        return super(JavaScriptEncoder,self).default(obj)

    def _js_clean(self, jsonstr):
        # This re replace is not ideal but at least the dirtyness of it is encapsulated in these classes
        # instead of plain str manipulation being done in the wild.
        def fix(matchobj):
            return _json.loads(matchobj.group(1))

        return self._js_re.sub(fix, jsonstr)

    def encode(self, obj):
        return self._js_clean(super(JavaScriptEncoder,self).encode(obj))

def _sanitize_value(value, errors='replace'):
    """
    JSONEncoder doesn't allow overriding the encoding of built-in types
    (in particular strings), and allows specifying an encoding but not
    a policy for errors when decoding strings to UTF-8. This function
    replaces all strings in a nested collection with unicode strings
    with 'replace' as the error policy.
    """
    newvalue = value
    if isinstance(value,str):
        newvalue = value.decode('utf8', errors)
    elif isinstance(value, dict):
        newvalue = {}
        for k, v in value.iteritems():
            if isinstance(v, (str,set,list,dict,tuple)):
                newvalue[k] = _sanitize_value(v)
            else:
                newvalue[k] = v
    elif isinstance(value,(list,tuple)):
        newvalue = []
        for v in value:
            if isinstance(v, (str,set,list,dict,tuple)):
                newvalue.append(_sanitize_value(v))
            elif hasattr(v, "result"):
                v.result = _sanitize_value(v.result)
                newvalue.append(v)
            else:
                newvalue.append(v)
    elif isinstance(value,set):
        newvalue = set()
        for v in value:
            if isinstance(v, (str,set,list,dict,tuple)):
                newvalue.add(_sanitize_value(v))
            else:
                newvalue.add(v)
    elif hasattr(value, "result"):
        newvalue.result = _sanitize_value(value.result)

    return newvalue

def json(value, **kw):
    """
    Serialize C{value} into a JSON string.

    If C{value} is callable, a decorated version of C{value} that serializes its
    return value will be returned.

        >>> value = (dict(a=1L), u"123", 123)
        >>> print json(value)
        [{"a": 1}, "123", 123]
        >>> @json
        ... def f():
        ...     return value
        ...
        >>> print f()
        [{"a": 1}, "123", 123]
        >>> from array import array
        >>> a1 = array('i', list(range(10)))
        >>> a2 = array('c', 'XYZZY')
        >>> a3 = (array('u',[unichr(i) for i in range(250,260)]))
        >>> [json(s) for s in (a1, a2, a3)]
        ['[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]', '"XYZZY"', '"\\\\u00fa\\\\u00fb\\\\u00fc\\\\u00fd\\\\u00fe\\\\u00ff\\\\u0100\\\\u0101\\\\u0102\\\\u0103"']
        >>> json([a1, a2, a3])
        '[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "XYZZY", "\\\\u00fa\\\\u00fb\\\\u00fc\\\\u00fd\\\\u00fe\\\\u00ff\\\\u0100\\\\u0101\\\\u0102\\\\u0103"]'
        >>> json({'properties' : [{ 'key' : 'a1', 'value' : a1 },{ 'key' : 'a2', 'value' : a2 },{ 'key' : 'a3', 'value' : a3 },] })
        '{"properties": [{"value": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "key": "a1"}, {"value": "XYZZY", "key": "a2"}, {"value": "\\\\u00fa\\\\u00fb\\\\u00fc\\\\u00fd\\\\u00fe\\\\u00ff\\\\u0100\\\\u0101\\\\u0102\\\\u0103", "key": "a3"}]}'

    @param value: An object to be serialized
    @type value: dict, list, tuple, str, etc. or callable
    @return: The JSON representation of C{value} or a decorated function
    @rtype: str, func
    """
    if callable(value):
        # Decorate the given callable
        def inner(*args, **kwargs):
            return json(value(*args, **kwargs))
        # Well-behaved decorators look like the decorated function
        inner.__name__ = value.__name__
        inner.__dict__.update(value.__dict__)
        inner.__doc__ = value.__doc__
        return inner
    else:
        # Simply serialize the value
        try:
            return _json.dumps(value, cls=ObjectEncoder, **kw)
        except UnicodeDecodeError:
            sanitized = _sanitize_value(value)
            return _json.dumps(sanitized, cls=ObjectEncoder, **kw)

def javascript(value):
    """A JavaScript encoder based on JSON. It encodes like normal JSON except it passes JavaScript objects un-encoded."""
    if callable(value):
        # Decorate the given callable
        def inner(*args, **kwargs):
            return javascript(value(*args, **kwargs))
        # Well-behaved decorators look like the decorated function
        inner.__name__ = value.__name__
        inner.__dict__.update(value.__dict__)
        inner.__doc__ = value.__doc__
        return inner
    else:
        # Simply serialize the value passed
        return _json.dumps(value, cls=JavaScriptEncoder)

def unjson(value, **kw):
    """
    Create the Python object represented by the JSON string C{value}.

        >>> jsonstr = '[{"a": 1}, "123", 123]'
        >>> print unjson(jsonstr)
        [{'a': 1}, '123', 123]

    @param value: A JSON string
    @type value: str
    @return: The object represented by C{value}
    """
    if 'cls' not in kw:
        kw['cls'] = StringifyingDecoder
    return _json.loads(value, **kw)
