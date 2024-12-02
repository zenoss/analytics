##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""BuiltInDS

Define a data source for RRD files that just appear without
additional configuration.
"""

from AccessControl.class_init import InitializeClass
from RRDDataSource import RRDDataSource

class BuiltInDS(RRDDataSource):

    sourcetypes = ('Built-In',)
    sourcetype = 'Built-In'
    
InitializeClass(BuiltInDS)
