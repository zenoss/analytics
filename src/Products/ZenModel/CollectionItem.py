##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""CollectionItem

Defines attributes for how a data source will be graphed
and builds the nessesary rrd commands.
"""

from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.deprecated import deprecated

@deprecated
def manage_addCollectionItem(context, id, deviceId, compPath, sequence,
                                                            REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    CollectionItems.
    '''
    unused(deviceId, compPath, sequence)
    ci = CollectionItem(id)
    context._setObject(id, ci)
    ci.deviceId = deviceId
    ci.compPath = compPath
    ci.sequence = sequence
    if REQUEST is not None:
        return REQUEST['RESPONSE'].redirect(context.absolute_url_path() +'/manage_main') 

addCollectionItem = DTMLFile('dtml/addCollectionItem',globals())


class CollectionItem(ZenModelRM):
  
    meta_type = 'CollectionItem'

    sequence = 0
    deviceId = ''
    compPath = ''
    deviceOrganizer = ''
    recurse = False
    
    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        {'id':'deviceId', 'type':'string', 'mode':'w'},
        {'id':'compPath', 'type':'string', 'mode':'w'},
        {'id':'deviceOrganizer', 'type':'string', 'mode':'w'},
        {'id':'recurse', 'type':'boolean', 'mode':'w'},
        )

    _relations = (
        ('collection', ToOne(ToManyCont,'Products.ZenModel.Collection','collection_items')),
        )
    
    factory_type_information = ( 
        { 
            'immediate_view' : 'editCollectionItem',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Collection Item'
                , 'action'        : 'editCollectionItem'
                , 'permissions'   : ( Permissions.view, )
                },
            )
        },
    )

    security = ClassSecurityInfo()

    def __init__(self, id, deviceId='', compPath='', deviceOrganizer='',
                    recurse=False, sequence=0, title=None, buildRelations=True):
        ZenModelRM.__init__(self, id, title, buildRelations)
        self.deviceId = deviceId
        self.compPath = compPath
        self.deviceOrganizer = deviceOrganizer
        self.recurse = recurse
        self.sequence = sequence


    def getDesc(self, withLink=True):
        ''' Return a string that represents this item
        '''
        thing = self.getRepresentedItem()
        if not thing:
            desc = 'missing'
        elif self.deviceId:
            if self.compPath:
                name = callable(thing.name) and thing.name() or thing.name
                desc = '%s %s' % (self.deviceId, name)
            else:
                desc = self.deviceId
            if withLink and thing:
                desc = '<a href="%s">%s</a>' % (thing.getPrimaryUrlPath(),desc)
        else:
            if withLink and thing:
                desc = '<a href="%s">%s</a>' % (thing.getPrimaryUrlPath(),
                    self.deviceOrganizer)
            else:
                desc = self.deviceOrganizer
            if self.recurse:
                desc += ' and suborganizers'
        return desc


    def getRepresentedItem(self):
        ''' Get the device organizer, component or device
        that this collection item represents
        '''
        thing = None
        if self.deviceId:
            thing = self.dmd.Devices.findDevice(self.deviceId)
            if self.compPath:
                for part in self.compPath.split('/'):
                    if part:
                        thing = getattr(thing, part, None)
                        if not thing:
                            break
        elif self.deviceOrganizer:
            try:
                thing = self.dmd.getObjByPath(self.deviceOrganizer.lstrip('/'))
            except KeyError:
                thing = None
        return thing


    def getDevicesAndComponents(self):
        ''' Return a list of the devices and components referenced by this item
        '''
        thing = self.getRepresentedItem()
        if not thing:
            stuff = []
        elif self.deviceId:
            stuff = [thing]
        elif self.recurse:
            stuff = thing.getSubDevices(lambda d: d.monitorDevice())
        else:
            stuff = [ dev for dev in thing.devices() if dev.monitorDevice() ]
        if len(stuff) > 1:
            stuff.sort(key=lambda x: x.primarySortKey())
        return stuff


    def getNumDevicesAndComponents(self):
        ''' Return the number of devices and components matched by this item
        '''
        things = self.getDevicesAndComponents()
        return len(things)
        
        

InitializeClass(CollectionItem)
