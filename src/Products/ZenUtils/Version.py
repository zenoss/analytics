##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Zenoss versioning module.

"""

from __future__ import print_function

import re

import six


def getVersionTupleFromString(versionString):
    """
    A utility function for parsing dot-delimited stings as a version tuple.

    # test some simple version formats
    >>> version = '1'
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = '1.0'
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = '1.0.0'
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = '1.0.2'
    >>> getVersionTupleFromString(version)
    (1, 0, 2)

    # here's one for Fedora
    >>> version = '2.6.17-1.2174_FC5'
    >>> getVersionTupleFromString(version)
    (2, 6, 17)

    # here's a bizzare one
    >>> version = '1a.23zzX.abs'
    >>> getVersionTupleFromString(version)
    (1, 23, 0)

    # checks against ints and floats being passed instead of strings
    >>> version = 1
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = 1.0
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = 0
    >>> getVersionTupleFromString(version)
    (0, 0, 0)
    >>> version = 'a.1.2'
    >>> getVersionTupleFromString(version)
    (0, 1, 2)
    >>> version = ''
    >>> getVersionTupleFromString(version)
    (0, 0, 0)
    >>> version = '5.2.25a'
    >>> getVersionTupleFromString(version)
    (5, 2, 25)
    """
    versionString = str(versionString)
    versions = re.split("[^0-9]+", versionString.strip())[:3]
    versions = [int(x or 0) for x in versions] + [0, 0, 0]
    return tuple(versions[:3])


class VersionError(Exception):
    pass


class IncomparableVersions(VersionError):
    pass


class ComponentVersionError(VersionError):
    pass


class VersionNotSupported(VersionError):
    pass


class Version(object):
    """
    A class for obtaining and manipulating version numbers as well as creating
    the necessary version files Zenoss utilizes.

    >>> v1 = Version('Zenoss', 0, 22)
    >>> v2 = Version('Zenoss', 0, 23, 4)
    >>> v3 = Version('Zenoss', 0, 23, 7)
    >>> v4 = Version('Zenoss', 1)
    >>> v5 = Version('Zenoss', 1, 0, 2)
    >>> v6 = Version('Zenoss', 1, 0, 2)
    >>> v7 = Version('Zenoss', 1, 0, 2, 15729)
    >>> v8 = Version('Zenoss', 1, 0, 2, 15730)
    >>> v9 = Version('Zenoss', 1, 0, 3, 15729)

    # test the display methods
    >>> v9.short()
    '1.0.3'
    >>> v9.long()
    'Zenoss 1.0.3'
    >>> v9.full()
    'Zenoss 1.0.3 r15729'
    >>> v2.tuple()
    (0, 23, 4)

    # comparisons
    >>> v1 > v2
    False
    >>> v3 > v2
    True
    >>> v4 < v3
    False
    >>> v4 > v5
    False
    >>> v6 > v5
    False
    >>> v6 >= v5
    True
    >>> v6 == v5
    True

    # comparison, one with a revision number
    >>> v7 > v6
    False

    # revision number comparisons
    >>> v7 > v8
    False
    >>> v8 > v9
    False

    # comparing non-Version objects with Version objects
    >>> '1.0.4' > v5
    True
    >>> (1,0,1) > v5
    False
    >>> 1 == v4
    True
    >>> v4 == 1.0
    True
    >>> '1.0' == v4
    True

    # comment/additional info
    >>> v10 = v9
    >>> v10.setComment('A super-secret squirrel release')
    >>> v10.full()
    'Zenoss 1.0.3 r15729 (A super-secret squirrel release)'
    """

    def __init__(
        self, name, major=0, minor=0, micro=0, revision=0, comment=""
    ):
        self.name = name
        self.major = major
        self.minor = minor
        self.micro = micro
        self.revision = revision
        self.comment = str(comment)

    def short(self):
        """
        Returns a string of just the version number.
        """
        return "%d.%d.%d" % (self.major, self.minor, self.micro)

    def long(self):
        """
        Returns a string with the software name and the version.
        """
        return "%s %s" % (self.name, self.short())

    def full(self):
        """
        Returns a string with the software name, the version number, and the
        subversion revision number, if defined.
        """
        comment = ""
        if self.comment:
            comment = " (" + self.comment + ")"
        return "%s%s%s" % (self.long(), self._formatSVNRevision(), comment)

    def tuple(self):
        """
        Return a version tuple.
        """
        return (self.major, self.minor, self.micro)

    def incrMajor(self):
        self.major += 1

    def incrMinor(self):
        self.minor += 1

    def incrMicro(self):
        self.micro += 1

    def setComment(self, comment):
        self.comment = comment

    def __eq__(self, other):
        if self is other:
            return True
        other = self._common_compare(other)
        if not isinstance(other, Version):
            return NotImplemented
        return self.tuple() == other.tuple()

    def __lt__(self, other):
        if self is other:
            return False
        other = self._common_compare(other)
        if not isinstance(other, Version):
            return NotImplemented
        return self.tuple() < other.tuple()

    def __le__(self, other):
        if self is other:
            return True
        other = self._common_compare(other)
        if not isinstance(other, Version):
            return NotImplemented
        return self.tuple() <= other.tuple()

    def _common_compare(self, other):
        other = Version.make(self.name, other)
        if other is None:
            return NotImplemented
        if self.name != other.name:
            raise IncomparableVersions()
        return other

    def _formatSVNRevision(self):
        svnrev = self.revision
        if svnrev:
            svnrev = " r%s" % svnrev
        else:
            svnrev = ""
        return svnrev

    def __repr__(self):
        return "%s(%s, %d, %d, %d,%s)" % (
            self.__class__.__name__,
            self.name,
            self.major,
            self.minor,
            self.micro,
            self._formatSVNRevision(),
        )

    def __str__(self):
        return "[%s, version %d.%d.%d%s]" % (
            self.name,
            self.major,
            self.minor,
            self.micro,
            self._formatSVNRevision(),
        )

    @classmethod
    def make(cls, name, obj):
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, (tuple, list)):
            version = ".".join(str(x) for x in obj)
            return cls.parse("%s %s" % (name, version))
        if any(
            isinstance(obj, x)
            for x in six.string_types + six.integer_types + (float,)
        ):
            return cls.parse("%s %s" % (name, obj))

    @classmethod
    def parse(cls, versionString):
        """
        Parse the version info from a string. This method is usable without
        having instantiated Version, and returns an instantiation.

        The expected form is the following:
            software_name W.X.Y rZ
        where W, X, and Y represent the major, minor, and micro version numbers
        and Z is the subversion revision number.

        Only the software name is required.

        The version number is expected to have at least a major version number.
        Minor and micro version numbers are optional, but if they are provided,
        they must be dot-delimited.

        Here are some example usages:

        >>> v = Version.parse('Zenoss')
        >>> repr(v)
        'Version(Zenoss, 0, 0, 0,)'
        >>> print(v)
        [Zenoss, version 0.0.0]

        >>> v = Version.parse('Zenoss 1')
        >>> repr(v)
        'Version(Zenoss, 1, 0, 0,)'
        >>> print(v)
        [Zenoss, version 1.0.0]

        >>> v = Version.parse('Zenoss 0.26.4')
        >>> repr(v)
        'Version(Zenoss, 0, 26, 4,)'
        >>> print(v)
        [Zenoss, version 0.26.4]

        >>> Version.parse('Zenoss 1.1.0') <= Version('Zenoss', 1, 0, 0)
        False
        >>> Version.parse('Zenoss 1.1.0') >= Version('Zenoss', 1, 0, 0)
        True
        >>> Version.parse('Zenoss 1.1.0') <= Version('Zenoss', 1, 1, 0)
        True
        >>> Version.parse('Zenoss 1.1.0') >= Version('Zenoss', 1, 1, 0)
        True

        >>> v = Version.parse('Zenoss 0.32.1 r13667')
        >>> repr(v)
        'Version(Zenoss, 0, 32, 1, r13667)'
        >>> print(v)
        [Zenoss, version 0.32.1 r13667]
        """
        versionParts = versionString.strip().split()
        name = versionParts.pop(0)

        try:
            # we want to always have a tuple of the right size returned,
            # regardless of the number of elements in the 'versions' iterable
            major, minor, micro = getVersionTupleFromString(
                versionParts.pop(0)
            )
            try:
                revision = versionParts.pop(0).strip("r")
            except IndexError:
                revision = ""
        except IndexError:
            major = minor = micro = 0
            revision = ""
        self = Version(name, major, minor, micro, revision)
        return self


def _test():
    import doctest

    doctest.testmod()


if __name__ == "__main__":
    _test()
