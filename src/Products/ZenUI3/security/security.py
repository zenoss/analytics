##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from AccessControl import getSecurityManager
from collective.beaker.interfaces import ISession
from Products.Five.viewlet import viewlet
from Products.Five.viewlet.manager import ViewletManagerBase
from zope import interface

from Products.ZenUtils.jsonutils import json
from Products.Zuul.interfaces import IAuthorizationTool

from .interfaces import ISecurityManager, IPermissionsDeclarationViewlet

ZAUTH_COOKIE = "ZAuthToken"


@interface.implementer(ISecurityManager)
class SecurityManager(ViewletManagerBase):
    """The Viewlet manager class for the permissions declaration"""


def permissionsForContext(context):
    """
    Given a context (zope object) returns all the permissions
    the logged in user has.
    """
    manager = getSecurityManager()
    all_permissions = context.zport.acl_users.possible_permissions()

    # filter out the ones we have in this context
    valid_permissions = [
        permission
        for permission in all_permissions
        if manager.checkPermission(permission, context)
    ]

    # turn the list into a dictionary to make it easier to look up on
    # the client side (just look up the key instead of iterating)
    perms = {}
    for permission in valid_permissions:
        perms[permission.lower()] = True
    return perms


@interface.implementer(IPermissionsDeclarationViewlet)
class PermissionsDeclaration(viewlet.ViewletBase):
    """This is responsible for sending to the client side
    which permissions the user has
    """

    def render(self):
        """Creates a global function in JavaScript that returns the
        json encoding of all the permissions available to the current
        user in the current context.  The permissions will be in the
        form of a dictionary.
        """
        self._setAuthorizationCookie()
        permissions = self.permissionsForCurrentContext()
        managedObjectGuids = self.getManagedObjectGuids(
            returnChildrenForRootObj=True
        )
        data = json(permissions)
        func = """
<script type="text/javascript">
    function _global_permissions(){
        return %s;
    }

    function _managed_objects(){
        return %s;
    }

    function _has_global_roles() {
        return %s
    }
</script>
        """ % (
            data,
            json(managedObjectGuids),
            str(self.hasGlobalRoles()).lower(),
        )
        return func

    def _setAuthorizationCookie(self):
        session = ISession(self.context.REQUEST)
        authorization = IAuthorizationTool(self.context)
        token = authorization.createAuthToken(self.request)

        self.request.response.setCookie(
            ZAUTH_COOKIE,
            token["id"],
            path="/",
            secure=session.secure,
            http_only=True,
        )

    def hasGlobalRoles(self):
        """
        @return True/False if the user has global roles
        """
        us = self.context.dmd.ZenUsers.getUserSettings()
        return not us.hasNoGlobalRoles()

    def permissionsForCurrentContext(self):
        """Given a context return a list of all the permissions the logged in
        user has.
        """
        return permissionsForContext(self.context)

    def getManagedObjectGuids(self, returnChildrenForRootObj=False):
        """
        If the currently logged in user is a restricted user this will return
        all of the guids for items he can administer.
        """
        guids = []
        us = self.context.dmd.ZenUsers.getUserSettings()
        if us.hasNoGlobalRoles():
            guids = us.getAllAdminGuids(
                returnChildrenForRootObj=returnChildrenForRootObj
            )
        return guids
