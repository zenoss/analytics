##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.CMFCore.utils import getToolByName

class Linkable:
    """ A mixin allowing an object to be the 
        endpoint of a Link object.
    """

    def _getLinkCatalog(self):
        try:
            return getToolByName(self.dmd.ZenLinkManager, self.link_catalog)
        except AttributeError:
            return None

    def index_links(self):
        # DEPRECATED
        pass

    def unindex_links(self):
        # DEPRECATED
        pass


class Layer2Linkable(Linkable):

    link_catalog = "layer2_catalog"

    def deviceId(self): raise NotImplementedError
    def interfaceId(self): raise NotImplementedError
    def macaddress(self): raise NotImplementedError
    def lanId(self): raise NotImplementedError


class Layer3Linkable(Linkable):

    link_catalog = "layer3_catalog"

    def deviceId(self): raise NotImplementedError
    def ipAddressId(self): raise NotImplementedError
    def networkId(self): raise NotImplementedError
    def interfaceId(self): raise NotImplementedError
