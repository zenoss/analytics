##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
This module patches OFS DTMLMethod to disable uploading files 
to dmd without authentication using a simple PUT HTTP call.
"""

from OFS.DTMLMethod import DTMLMethod
from Products.ZenUtils.Utils import monkeypatch
from zExceptions import MethodNotAllowed


@monkeypatch(DTMLMethod)
def PUT(self, REQUEST, RESPONSE):
    """
    Disable HTTP PUT for preventing upload to dmd without authentication
    """
    raise MethodNotAllowed('Method not supported for this resource.')
