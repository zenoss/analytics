##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface

class IFormBuilder(Interface):
    """
    Builds the config for an Ext FormPanel based on the schema of the interface
    of the context.
    """
    def fields(fieldFilter=None):
        """
        Get the schema of the context and return the dictionary that will be
        used to render the form.
        @parameter fieldFilter: function to filter fields; return true to include, false to exclude. If none, all are included
        @type fieldFilter: function
        """
    def render():
        """
        Return the Ext config for the form.
        @parameter filter: funtion to filter fields; return true to include, false to exclude. If none, all are included
        @type filter: function
        """
