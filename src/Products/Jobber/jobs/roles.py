##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from .job import Job


class DeviceSetLocalRolesJob(Job):
    """Takes a device organizer and calls setAdminLocalRoles on each device.

    When someone updates a role on an organizer this is necessary to make
    sure that user has permission on each of the devices in that organizer.
    """

    name = "Products.Jobber.DeviceSetLocalRolesJob"

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job."""
        return "Device Set Local Roles"

    @classmethod
    def getJobDescription(cls, **kwargs):
        """Return a description of the job."""
        return "Setting Administrative roles"

    def _run(self, organizerUid, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.log.info("About to set local roles for uid: %s ", organizerUid)
        organizer = self.dmd.unrestrictedTraverse(organizerUid)
        organizer._setDeviceLocalRoles()


from Products.Jobber.zenjobs import app
app.register_task(DeviceSetLocalRolesJob)
