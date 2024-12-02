
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenRelations.RelSchema import *

class TemplateContainer(object):
    """
    This mixin is so that different classes can sit on the other
    end of the RRDTemplate.deviceClass method.
    """

    meta_type = 'TemplateContainer'

    _relations = (
        # deviceClass is named as such for sad, historical reasons.
        # Currently the subclasses of TemplateContainer are either
        # a DeviceClass or a MonitorClass.
        ('rrdTemplates', 
            ToManyCont(ToOne, 'Products.ZenModel.RRDTemplate', 'deviceClass')),
    )
