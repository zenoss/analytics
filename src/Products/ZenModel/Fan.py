##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Fan

Fan is an abstraction of any fan on a device. CPU, chassis, etc.

$Id: Fan.py,v 1.7 2004/04/06 22:33:24 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from AccessControl.class_init import InitializeClass
from math import isnan
from Products.ZenRelations.RelSchema import *

from HWComponent import HWComponent

from Products.ZenModel.ZenossSecurity import *

class Fan(HWComponent):
    """Fan object"""

    portal_type = meta_type = 'Fan'

    state = "unknown"
    type = "unknown"

    _properties = HWComponent._properties + (
        {'id':'state', 'type':'string', 'mode':'w'},
        {'id':'type', 'type':'string', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(ToManyCont, "Products.ZenModel.DeviceHW", "fans")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'Fan',
            'meta_type'      : 'Fan',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Fan_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addFan',
            'immediate_view' : 'viewFan',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewFan'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
            )
          },
        )


    def rpmString(self):
        """
        Return a string representation of the RPM
        """
        rpm = self.rpm()
        return rpm is None and "unknown" or "%lrpm" % (rpm,)


    def rpm(self, default=None):
        """
        Return the current RPM
        """
        rpm = self.cacheRRDValue('rpm', default)
        if rpm is not None and not isnan(rpm):
            return long(rpm)
        return None


    def viewName(self):
        return self.id
    name = viewName


InitializeClass(Fan)
