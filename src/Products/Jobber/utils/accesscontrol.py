##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass as initClass


class ZClassSecurityInfo(object):
    """Use AccessControl.ClassSecurityInfo as a function decorator."""

    def __init__(self):
        """Initialize a ZClassSecurityInfo instance."""
        self.__csi = ClassSecurityInfo()

    def private(self, f):
        """Declare the given function as private."""
        self.__csi.declarePrivate(f.func_name)
        return f

    def protected(self, permission):
        """Declare the given function as protected."""

        def wrap(f):
            self.__csi.declareProtected(permission, f.func_name)
            return f

        return wrap

    def __getattr__(self, name):
        """Return the value of the named attribute."""
        return getattr(self.__csi, name)


def ZInitializeClass(cls):
    """Use AccessControl.class_init.InitializeClass as a class decorator."""
    initClass(cls)
    return cls
