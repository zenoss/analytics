##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""HardDisk
Hard Disk is the physical spindles that can be aggregated into
storage pools etc.
"""


from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass

from Products.ZenRelations.RelSchema import ToOne, ToManyCont

from HWComponent import HWComponent

def manage_addHardDisk(context, id, title = None, REQUEST = None):
    """make a filesystem"""
    hd = HardDisk(id, title)
    context._setObject(id, hd)
    hd = context._getOb(id)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 

addHardDisk = DTMLFile('dtml/addHardDisk',globals())


class HardDisk(HWComponent):
    """HardDisk object"""

    portal_type = meta_type = 'HardDisk'

    manage_editHardDiskForm = DTMLFile('dtml/manageEditHardDisk',globals())
    
    description = ""
    hostresindex = 0

    _properties = HWComponent._properties + (
                 {'id':'description', 'type':'string', 'mode':'w'},
                 {'id':'hostresindex', 'type':'int', 'mode':'w'},
                )    

    _relations = HWComponent._relations + (
        ("hw", ToOne(ToManyCont, "Products.ZenModel.DeviceHW", "harddisks")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'HardDisk',
            'meta_type'      : 'HardDisk',
            'description'    : """Hard Diskclass""",
            'icon'           : 'HardDisk_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addHardDisk',
            'immediate_view' : 'viewHardDisk',
            'actions'        :
            ( 
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },                
            )
          },
        )

    def viewName(self):
        return self.description if self.description else self.title

    name = primarySortKey = viewName


InitializeClass(HardDisk)
