##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl import ClassSecurityInfo
from Products.ZenWidgets import messaging

class ZenPacker(object):
    security = ClassSecurityInfo()

    security.declareProtected('Manage DMD', 'addToZenPack')
    def addToZenPack(self, ids=(), organizerPaths=(), pack=None, REQUEST=None):
        "Add elements from a displayed list of objects to a ZenPack"
        from Products.ZenModel.ZenPackable import ZenPackable
        from Products.ZenModel.ZenPack import ZenPack
        ids = list(ids) + list(organizerPaths)
        message = "You must provide a valid ZenPack"
        if pack:
            pack = self.dmd.ZenPackManager.packs._getOb(pack)
            message = 'Saved to %s' % pack.id
            if ids:
                for id in ids:
                    try:
                        obj = self.findObject(id)
                    except AttributeError as ex:
                        message = str(ex)
                        break
                    obj.buildRelations()
                    pack.packables.addRelation(obj)
            else:
                if isinstance(self, ZenPackable):
                    self.buildRelations()
                    pack.packables.addRelation(self)
                else:
                    message = 'Nothing to save'
        if REQUEST:
            if isinstance(pack, ZenPack):
                messaging.IMessageSender(self).sendToBrowser(
                    'Add To ZenPack', message)
            return REQUEST['RESPONSE'].redirect('/zport/dmd/ZenPackManager' +
                    '/packs/%s' % pack.id if pack else '')

    def findObject(self, id):
        "Ugly hack for inconsistent object structure accross Organizers"
        result = []
        try:
            result.append(self._getOb(id))
        except AttributeError:
            pass
        for name, relationship in self._relations:
            try:
                result.append(getattr(self, name)._getOb(id))
            except AttributeError:
                pass
        if len(result) == 0:
            try:
                if isinstance(id, unicode):
                    id = id.encode('utf-8')
                result.append(self.dmd.unrestrictedTraverse(id))
            except KeyError:
                pass
        if len(result) == 1:
            return result[0]
        raise AttributeError('Cannot find a unique %s on %s' % (id, self.id))


    def eligiblePacks(self):
        """
        Return a list of zenpacks that objects can be added to.  (The
        development mode zenpacks.)
        """
        return [zp for zp in self.dmd.ZenPackManager.packs() 
                if zp.isDevelopment()]
