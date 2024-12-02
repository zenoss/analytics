##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
ZenPackPersistence
'''

from zope.interface import implements
from Products.ZenModel.interfaces import IIndexed

ZENPACK_PERSISTENCE_CATALOG = 'zenPackPersistence'

import logging
log = logging.getLogger('ZenPackPersistence')

def CreateZenPackPersistenceCatalog(dmd):
    '''
    Create the zenPackPersistence catalog if it does not exist.
    Return the catalog
    '''
    from Products.ZCatalog.ZCatalog import manage_addZCatalog
    from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex
    zcat = getattr(dmd, ZENPACK_PERSISTENCE_CATALOG, None)
    if zcat is None:
        manage_addZCatalog(dmd, ZENPACK_PERSISTENCE_CATALOG,
                                ZENPACK_PERSISTENCE_CATALOG)
        zcat = dmd._getOb(ZENPACK_PERSISTENCE_CATALOG)
        cat = zcat._catalog
        cat.addIndex('getZenPackName',makeCaseSensitiveFieldIndex('getZenPackName'))
        cat.addColumn('id')
        cat.addColumn('getPrimaryId')
    return zcat


def GetCatalogedObjects(dmd, packName):
    """
    Return a list of all the objects in the zenPackPersistence catalog
    for the given zenPack name.
    If the catalog is not found, return None.
    """
    zcat = getattr(dmd, ZENPACK_PERSISTENCE_CATALOG, None)
    if zcat is None:
        result = None
    else:
        result = []
        brains = zcat(dict(getZenPackName=packName))
        for brain in brains:
            try:
                obj = brain.getObject()
                result.append(obj)
            except KeyError as e:
                log.warn('catalog object %s not found in system', e)
    return result


class ZenPackPersistence(object):
    '''
    This is a mix-in class that should be used whenever a ZenPack-supplied
    class is going to be stored persistently in the zodb.  It provides
    for a catalog to associate objects in zodb with the ZenPacks that provide
    those objects' classes.
    
    The motivation for this is that we usually need to delete all instances
    of zenpack-supplied classes when that zenpack is deleted.  This is
    because the class for those objects no longer exists and they are just
    sad, broken, unloved objects in the zodb at that point.  This is 
    undesirable.
    
    IMPORTANT: This should be the first class listed in any subclasses's
    list of parents.  Otherwise the manage_* methods of the other classes
    will likely be called and these skipped.
    '''
    implements(IIndexed)

    # Subclasses should set this to the id of the ZenPack or they
    # should override getZenPackName()
    # ZENPACKID = 'ZenPacks.my.name'

    def getZenPackName(self):
        '''
        '''
        if not self.ZENPACKID:
            from ZenPack import ZenPackException
            raise ZenPackException('The class %s must define ZENPACKID ' %
                    str(self.__class__) +
                    'or override getZenPackName().')
        # Should we check to make sure ZENPACKID matches the name of an
        # installed ZenPack?
        return self.ZENPACKID


    def getZenPack(self, context):
        """
        Return the ZenPack instance that provides this object.
        """
        return context.dmd.ZenPackManager.packs._getOb(
                                            self.getZenPackName(), None)
    
    
    def path(self, *parts):
        """
        Return the path to the installed ZenPack directory or a subdirectory.
        Example: zenpack.path('libexec') would return something like
        $ZENHOME/ZenPacks/ZenPacks.Me.MyZenPack/ZenPacks/Me/MyZenPack/libexec
        """
        zp = self.getZenPack(self)
        return zp.path(*parts)


    # index_object and unindex_object are overridden so that instances
    # can participate in other catalogs, not just the 
    # ZENPACK_PERSISTENCE_CATALOG.
    # If we used the standard method of just setting default_catalog in
    # this class then ZenPacks would not be able to override Zenoss
    # classes that already participate in catalogs, eg DeviceClass.
    
    def index_object(self, idxs=None):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, ZENPACK_PERSISTENCE_CATALOG, None)
        if cat is not None:
            cat.catalog_object(self, self.getPrimaryId())            
        super(ZenPackPersistence, self).index_object(idxs=None)


    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        #FIXME THIS WON'T WORK IF WE DELETE FROM THE ZENPACK PAGE BECAUSE WE CAN'T FIND THE CATALOG -EAD
        cat = getattr(self, ZENPACK_PERSISTENCE_CATALOG, None)
        if cat is not None:
            cat.uncatalog_object(self.getPrimaryId())
        super(ZenPackPersistence, self).unindex_object()
