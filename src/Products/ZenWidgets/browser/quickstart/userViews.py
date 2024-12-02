##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile

from Products.ZenModel.Quickstart import getTopQuickstartStep
from Products.ZenUtils import Ext
from Products.ZenUtils.csrf import check_csrf_token

log = logging.getLogger("zen.widgets.userviews")


class SetAdminPasswordException(Exception):
    """There was a problem setting the admin password."""


class CreateUserView(BrowserView):
    """Creates the initial user and sets the admin password."""

    __call__ = ZopeTwoPageTemplateFile("templates/createuser.pt")

    @Ext.form_action
    def createUser(self):
        """
        Handles form submission for setting the admin password and creating
        an initial user.
        """
        check_csrf_token(self.request)

        response = Ext.FormResponse()

        adminPassword = self.request.form.get("admin-password1")
        userName = self.request.form.get("username")
        userPassword = self.request.form.get("password1")
        emailAddress = self.request.form.get("emailAddress")

        zenUsers = getToolByName(self.context, "ZenUsers")

        # Set admin password
        try:
            admin = zenUsers.getUserSettings("admin")
            admin.manage_editUserSettings(
                password=adminPassword,
                sndpassword=adminPassword,
                roles=("ZenManager", "Manager"),
                oldpassword="zenoss",
            )
        except Exception:
            log.exception("Failed to set admin password")
            response.error(
                "admin-password1",
                "There was a problem setting the admin password.",
            )

        if not zenUsers.checkValidId(userName) is True:
            response.error("username", "That username already exists.")
        else:
            ret = zenUsers.manage_addUser(
                userName,
                userPassword,
                ("Manager",),
                REQUEST=None,
                email=emailAddress,
            )
            if ret is None:
                response.error(
                    "username",
                    "We were unable to add a user at this time."
                    " Check your installation.",
                )

        if not response.has_errors():
            # Log out, so the form can log us in as the new user
            _ = self.context.getPhysicalRoot().acl_users
            self.context.acl_users.resetCredentials(
                self.request, self.request.response
            )

        # Don't run the quickstart next time
        self.context.dmd._rq = True

        # Send us on our way
        nextStep = getTopQuickstartStep(self.context.dmd)
        response.redirect(nextStep)
        return response
