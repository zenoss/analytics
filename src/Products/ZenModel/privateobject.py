##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from zope.component import subscribers
from .interfaces import IPrivateObjectAdapter


def is_private(ob):
    """
    Do any registered private object adapters define this object as private?
    """
    for adapted in subscribers([ob], IPrivateObjectAdapter):
        if adapted.is_private():
            return True
    return False

