##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface
from zope.viewlet.interfaces import IViewletManager

class IExtDirectJavaScriptManager(IViewletManager):
    """
    A viewlet manager to register API providers.
    """

class IJsonApiJavaScriptManager(IViewletManager):
    """
    A viewlet manager to register API providers.
    """

class IExtDirectJavaScriptAndSourceManager(IExtDirectJavaScriptManager):
    """
    A viewlet manager to publish Ext javascript resources and register API
    providers.
    """

class IDirectProviderDefinition(Interface):
    def render():
        """
        Generate client-side stub defining a provider.
        """
