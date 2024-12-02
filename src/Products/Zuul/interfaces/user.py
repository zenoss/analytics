##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from Products.Zuul.interfaces import IFacade, IInfo


class IUserFacade(IFacade):
    """
    Responsible for managing users
    """
    pass

class IUserInfo(IInfo):
    """
    Marker interface for user info object.
    """
