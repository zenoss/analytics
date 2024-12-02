##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from ManagedEntity import ManagedEntity
from DeviceComponent import DeviceComponent
from Products.ZenRelations.RelSchema import ToMany


class OSComponent(DeviceComponent, ManagedEntity):
    """
    Logical Operating System component like a Process, IpInterface, etc.
    """
    isUserCreatedFlag = False

    _relations = ManagedEntity._relations + (
        ("links", ToMany(ToMany, "Products.ZenModel.Link", "endpoints")),
    )

    def setUserCreateFlag(self):
        """
        Sets self.isUserCreatedFlag to True.  This indicated that the
        component was created by a user rather than via modelling.
        """
        self.isUserCreatedFlag = True


    def isUserCreated(self):
        """
        Returns the value of isUserCreated.  See setUserCreatedFlag() above.
        """
        return self.isUserCreatedFlag


    def device(self):
        """
        Return our device object for DeviceResultInt.
        """
        os = self.os()
        if os: return os.device()


    def manage_deleteComponent(self, REQUEST=None):
        """
        Delete OSComponent
        """
        url = None
        if REQUEST is not None:
            url = self.device().os.absolute_url_path()
        self.getPrimaryParent()._delObject(self.id)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)


    def manage_updateComponent(self, datamap, REQUEST=None):
        """
        Update OSComponent
        """
        url = None
        if REQUEST is not None:
            url = self.device().os.absolute_url_path()
        self.getPrimaryParent()._updateObject(self, datamap)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)


    def getPrettyLink(self):
        """
        Gets a link to this object, plus an icon
        """
        template = ("<a href='%s' class='prettylink'>"
                    "<div class='device-icon-container'> "
                    "<img class='device-icon' src='%s'/> "
                    "</div>%s</a>")
        icon = self.getIconPath()
        href = self.getPrimaryUrlPath()
        name = self.titleOrId()
        return template % (href, icon, name)
