##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""Collection
Holds an assortment of devices and/or components on a multi-style report.
"""
import sys

from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo, Permissions
from AccessControl.class_init import InitializeClass
from zope.component import getUtility
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from Products.ZenUtils.Utils import resequence
from Products.ZenWidgets import messaging
from Products.ZenUtils.deprecated import deprecated
from Products.ZenMessaging.audit import audit

@deprecated
def manage_addCollection(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    Collections.
    '''
    c = Collection(id)
    context._setObject(id, c)
    if REQUEST is not None:
        return REQUEST['RESPONSE'].redirect(context.absolute_url_path() +'/manage_main')

addCollection = DTMLFile('dtml/addCollection',globals())


class Collection(ZenModelRM):
    """
    Holds an assortment of devices and/or components on a multi-style report.
    """

    meta_type = 'Collection'

    _properties = (
        )

    _relations =  (
        ('report',
            ToOne(ToManyCont, 'Products.ZenModel.MultiGraphReport', 'collections')),
        ('collection_items',
            ToManyCont(ToOne, 'Products.ZenModel.CollectionItem', 'collection')),
        )

    factory_type_information = (
    {
        'immediate_view' : 'editCollection',
        'actions'        :
        (
            { 'id'            : 'edit'
            , 'name'          : 'Collection'
            , 'action'        : 'editCollection'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()


    def createCollectionItem(self, orgPath='', devId='', compPath='',
                            recurse=False, checkExists=False):
        ''' Create and insert a new CollectionItem based either on the
        orgPath or on devId/compPath.  Returns the new item.
        '''
        from CollectionItem import CollectionItem
        ci = CollectionItem(self.getUnusedId('collection_items', 'Item'))
        if orgPath:
            ci.deviceOrganizer = orgPath
        else:
            ci.deviceId = devId
            ci.compPath = compPath
        ci.recurse = recurse
        ci.sequence = len(self.collection_items())
        self.collection_items._setObject(ci.id, ci)
        ci = self.collection_items._getOb(ci.id)
        # This check happens after the _setObject so that ci has full
        # aq wrapper in case it needs it.
        if checkExists and not ci.getRepresentedItem():
            self.collection_items._delObject(ci.id)
            ci = None
        return ci


    security.declareProtected('Manage DMD', 'manage_addCollectionItem')
    def manage_addCollectionItem(self, itemType,
            deviceIds=(), componentPaths=(), deviceClasses=(), systems=(),
            groups=(), locations=(), recurse=False, REQUEST=None):
        ''' Create a new CollectionItem and add to this collection
        '''
        count = 0
        if itemType == 'devcomp':
            if not deviceIds:
                deviceIds = []
            if not componentPaths:
                componentPaths = ['']
            for i, devId in enumerate(deviceIds):
                for cPath in componentPaths:
                    ci = self.createCollectionItem(devId=devId, compPath=cPath,
                        recurse=False, checkExists=True)
                    if ci:
                        count += 1
        if itemType == 'deviceClass':
            for dClass in deviceClasses:
                self.createCollectionItem(
                                    orgPath='/Devices' + dClass, recurse=recurse)
            count += 1
        if itemType == 'system':
            for system in systems:
                self.createCollectionItem(
                                    orgPath='/Systems' + system, recurse=recurse)
                count += 1
        if itemType == 'group':
            for group in groups:
                self.createCollectionItem(
                                    orgPath='/Groups' + group, recurse=recurse)
                count += 1
        if itemType == 'location':
            for loc in locations:
                self.createCollectionItem(
                                    orgPath='/Locations' + loc, recurse=recurse)
                count += 1

        if REQUEST:
            audit('UI.Collection.AddItem', self.id, itemType=itemType, deviceIds=deviceIds,
                  componentPaths=componentPaths, deviceClasses=deviceClasses, systems=systems,
                  groups=groups, locations=locations)
            messaging.IMessageSender(self).sendToBrowser(
                'Items Added',
                ' %s item%s added' % (count, count > 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_deleteCollectionItems')
    def manage_deleteCollectionItems(self, ids=(), REQUEST=None):
        """ Delete collection items from this report
        """
        for id in ids:
            deletedItem = self.collection_items._getOb(id)
            self.collection_items._delObject(id)
            if REQUEST:
                contents = None
                if deletedItem.getRepresentedItem():
                    contents = deletedItem.getRepresentedItem().id
                audit('UI.Collection.DeleteItem', self.id, item=deletedItem.id,
                      contents=contents)

        self.manage_resequenceCollectionItems()
        if REQUEST:
            count = len(ids)
            messaging.IMessageSender(self).sendToBrowser(
                'Items Deleted',
                ' %s item%s deleted' % (count, count > 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceCollectionItems')
    def manage_resequenceCollectionItems(self, seqmap=(), origseq=(),
                                                                REQUEST=None):
        """Reorder the sequence of the items.
        """
        retval = resequence(self, self.collection_items(), seqmap, origseq, REQUEST)
        if REQUEST:
            audit('UI.Collection.ResequenceItems', self.id, sequence=seqmap,
                  oldData_={'sequence':origseq})
        return retval


    security.declareProtected('Manage DMD', 'getItems')
    def getItems(self):
        ''' Return an ordered list of CollectionItems
        '''
        def itemKey(a):
            try:
                return int(a.sequence)
            except ValueError:
                return sys.maxint
        return sorted(self.collection_items(), key=itemKey)


    def getNumItems(self):
        ''' Return the number of collection items
        '''
        return len(self.collection_items())


    def getDevicesAndComponents(self):
        ''' Return a deduped list of devices and components represented
        by this collection's collectionitems
        '''
        things = []
        tset = set()
        for collectionItem in self.getItems():
            devsAndComps = collectionItem.getDevicesAndComponents()
            for devOrComp in devsAndComps:
                tid = devOrComp.getPrimaryId()
                if tid not in tset:
                    tset.add(tid)
                    things.append(devOrComp)
        return things

InitializeClass(Collection)
