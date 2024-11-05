##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os

from pathlib2 import PurePath, Path

__all__ = (
    "binPath",
    "isZenBinFile",
    "varPath",
    "zenPath",
    "zenpathjoin",
    "zenpathsplit",
    "zopePath",
)


def zenpathsplit(pathstring):
    """Returns a path string without any spaces in its parts.

    >>> zenpathsplit('/zport/dmd/Devices')
    ['zport', 'dmd', 'Devices']
    >>> zenpathsplit(' a /b / c')
    ['a', 'b', 'c']
    >>> zenpathsplit('')
    []
    >>> zenpathsplit('/')
    []
    >>> zenpathsplit('//')
    ['//']
    >>> zenpathsplit('///')
    []

    @param pathstring: a path inside of ZENHOME
    @type pathstring: string
    @return: a path
    @rtype: string
    """
    path = _normalize_path(pathstring)
    if not path.parts:
        return []
    return list(path.parts if path.parts[0] != "/" else path.parts[1:])


def zenpathjoin(path):
    """Returns a joined path in its string form.

    >>> zenpathjoin(('zport', 'dmd', 'Devices', 'Server'))
    '/zport/dmd/Devices/Server'
    >>> zenpathjoin(('', 'zport', 'dmd', 'Devices', 'Server'))
    '/zport/dmd/Devices/Server'
    >>> zenpathjoin('opt')
    '/opt'
    >>> zenpathjoin(['opt', 'a', 'b'])
    '/opt/a/b'
    >>> zenpathjoin(['', 'opt', 'a', 'b'])
    '/opt/a/b'
    >>> zenpathjoin(['', 'opt', '', 'a', 'b'])
    '/opt/a/b'

    @param path: One or more parts of a path.
    @type path: string or sequence
    @return: a path
    @rtype: string
    """
    parts = [path] if isinstance(path, basestring) else path
    return str(PurePath("/").joinpath(*parts))


def varPath(*args):
    """Return a path relative to /var/zenoss specified by joining args.

    The path is not guaranteed to exist on the filesystem.
    """
    return _pathjoin("/var/zenoss", *args)


def zenPath(*args):
    """Return a path relative to $ZENHOME specified by joining args.

    The path is not guaranteed to exist on the filesystem.

    >>> import os
    >>> zenHome = os.environ['ZENHOME']
    >>> zenPath() == zenHome
    True
    >>> zenPath('') == zenHome
    True
    >>> zenPath('Products') == os.path.join(zenHome, 'Products')
    True
    >>> zenPath('/Products/') == zenPath('Products')
    True
    >>>
    >>> zenPath('Products', 'foo') == zenPath('Products/foo')
    True

    # NB: The following is *NOT* true for os.path.join()
    >>> zenPath('/Products', '/foo') == zenPath('Products/foo')
    True
    >>> products = zenPath('Products')
    >>> zenPath(products) == products
    True
    >>> product_colors = zenPath('Products', 'orange', 'blue')
    >>> zenPath(zenPath('Products'), 'orange', 'blue') == product_colors
    True

    # Pathological case
    # NB: need to expand out the array returned by split()
    >>> zenPath() == zenPath( *'/'.split(zenPath()) )
    True

    @param *args: path components starting from $ZENHOME
    @type *args: strings
    @todo: determine what the correct behaviour should be if $ZENHOME is a
        symlink!
    """
    zenhome = os.environ.get("ZENHOME", "")
    return _pathjoin(zenhome, *args)


def zopePath(*args):
    """
    Similar to zenPath() except that this constructs a path based on
    ZOPEHOME rather than ZENHOME.  This is useful on the appliance.
    If ZOPEHOME is not defined or is empty then return ''.
    NOTE: A non-empty return value does not guarantee that the path exists,
    just that ZOPEHOME is defined.

    >>> import os
    >>> zopeHome = os.environ.setdefault('ZOPEHOME', '/something')
    >>> zopePath('bin') == os.path.join(zopeHome, 'bin')
    True
    >>> zopePath(zopePath('bin')) == zopePath('bin')
    True

    @param *args: path components starting from $ZOPEHOME
    @type *args: strings
    """
    zopehome = os.environ.get("ZOPEHOME", "")
    return _pathjoin(zopehome, *args)


def binPath(filename):
    """
    Search for the given file in a list of possible locations.  Return
    either the full path to the file or '' if the file was not found.

    >>> len(binPath('zenoss')) > 0
    True
    >>> len(binPath('zeoup.py')) > 0 # This doesn't exist in Zope 2.12
    False
    >>> binPath('Idontexistreally') == ''
    True

    @param fileName: name of executable
    @type fileName: string
    @return: path to file or '' if not found
    @rtype: string
    """
    paths = (
        Path(zenPath("bin", filename)),
        Path(zenPath("libexec", filename)),
        Path(zopePath("bin", filename)),
        Path(_pathjoin("/usr/lib/nagios/plugins", filename)),
        Path(_pathjoin("/usr/lib64/nagios/plugins", filename)),
    )
    return str(next((p for p in paths if p.is_file()), ""))


def isZenBinFile(name):
    """Check if given name is a valid file in $ZENHOME/bin."""
    return Path(binPath(name)).is_file()


def _normalize_path(pathstring):
    """Return a path string with no spaces surrounding each path part.

    Trailing slash is also removed.

    >>> _normalize_path('/opt/')
    PurePosixPath('/opt')
    >>> _normalize_path('/ a/b / c /d')
    PurePosixPath('/a/b/c/d')
    >>> _normalize_path('opt/')
    PurePosixPath('opt')
    >>> _normalize_path(' a/b / c /d')
    PurePosixPath('a/b/c/d')
    """
    return PurePath(*(p.strip() for p in PurePath(pathstring).parts))


def _pathjoin(basepath, *parts):
    """Returns a path string constructed from the arguments.

    The first argument ('base_path') is always the root part of the path.
    This differs from os.path.join's behavior of discarding earlier path
    parts if later path parts have a leading slash.

    The base_path and *args are two paths to be joined.  If the left-most
    parts of *args matches base_path, only the parts after the match are
    used in the resulting path.

    >>> _pathjoin('/opt/')
    '/opt'
    >>> _pathjoin('/opt', '/a/', 'b/')
    '/opt/a/b'
    >>> _pathjoin('/opt', _pathjoin('/opt', 'a', 'b'))
    '/opt/a/b'
    >>> _pathjoin('/opt/a', '/opt/a/b')
    '/opt/a/b'
    >>> _pathjoin('/opt/a', 'opt/a/b')
    '/opt/a/b'
    >>> _pathjoin('/opt/a', '/opt/b/c')
    '/opt/a/opt/b/c'
    >>> _pathjoin('/bin', '/opt/bin/c')
    '/bin/opt/bin/c'
    >>> _pathjoin('bin', 'opt/bin/c')
    'bin/opt/bin/c'
    >>> _pathjoin('bin', '/opt/bin/c')
    'bin/opt/bin/c'
    >>> _pathjoin('bin', 'bin/c')
    'bin/c'
    >>> _pathjoin('a')
    'a'
    >>> _pathjoin('/a')
    '/a'
    >>> _pathjoin('/a', 'b', 'c')
    '/a/b/c'
    >>> _pathjoin('/a', '/b', '/c')
    '/a/b/c'
    >>> _pathjoin('/a', 'b', '/c')
    '/a/b/c'
    >>> _pathjoin('a', 'b', 'c')
    'a/b/c'
    >>> _pathjoin('a', '/b', '/c')
    'a/b/c'
    >>> _pathjoin('a', 'b', '/c')
    'a/b/c'
    >>> _pathjoin('a', '')
    'a'
    >>> _pathjoin('a', '', 'b')
    'a/b'
    >>> _pathjoin('/a ', ' b ', '/ c', '/d ')
    '/a/b/c/d'
    >>> _pathjoin('/a/b', '/a/b', 'c')
    '/a/b/c'
    >>> _pathjoin('/a/b', '/a/', 'b/', 'c')
    '/a/b/c'
    >>> _pathjoin('a/b', '/a/b', 'c')
    'a/b/c'
    >>> _pathjoin('a/b', 'a', 'b', 'c')
    'a/b/c'

    @param base_path: Base path to assume everything is rooted from.
    @type base_path: string
    @param *args: Path parts that follow base_path.
    @type *args: Sequence of strings
    @return: sanitized path
    @rtype: string
    """
    base = _normalize_path(basepath)
    if not parts:
        return str(base)
    subpath = PurePath(*(p.strip("/").strip() for p in parts))
    relbase = PurePath(*base.parts[1:]) if base.is_absolute() else base
    if relbase in subpath.parents:
        subpath = subpath.relative_to(relbase)
    return str(base.joinpath(subpath))
