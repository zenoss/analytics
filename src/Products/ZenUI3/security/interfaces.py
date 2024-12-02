##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.viewlet.interfaces import IViewletManager, IViewlet


class ISecurityManager(IViewletManager):
    """
    The Viewlet manager for the security declaratives
    """


class IPermissionsDeclarationViewlet(IViewlet):
    """
    Will return to the client side all of our security declaritives
    """
