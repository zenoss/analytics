##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD
from Products.ZenWidgets import messaging

UNLOCKED = 0
DELETE_LOCKED = 1
UPDATE_LOCKED = 2


class Lockable(object):

    sendEventWhenBlockedFlag = False
    modelerLock = UNLOCKED

    security = ClassSecurityInfo()

    def getNextLockableParent(self, obj=None):
        if not obj: obj = self
        if obj.getPrimaryParent() == self.getDmd():
            return None
        elif isinstance(obj.getPrimaryParent(), Lockable):
            return obj.getPrimaryParent()
        else:
            return self.getNextLockableParent(obj.getPrimaryParent())

    def sendEventWhenBlocked(self):
        if self.sendEventWhenBlockedFlag:
            return True
        return False
        '''
        else:
            lockableParent = self.getNextLockableParent()
            if lockableParent:
                return lockableParent.sendEventWhenBlocked()
            else:
                return False
        '''

    def isUnlocked(self):
        if self.modelerLock == UNLOCKED:
                return True
        return False

    def isLockedFromDeletion(self):
        if (self.modelerLock == DELETE_LOCKED 
            or self.modelerLock == UPDATE_LOCKED):
            return True
        return False
        '''
        else:
            lockableParent = self.getNextLockableParent()
            if lockableParent:
                return lockableParent.isLockedFromDeletion()
            else:
                return False
        '''

    def isLockedFromUpdates(self):
        if self.modelerLock == UPDATE_LOCKED: 
            return True
        return False
        '''
        else:
            lockableParent = self.getNextLockableParent()
            if lockableParent:
                return lockableParent.isLockedFromUpdates()
            else:
                return False
        '''

    security.declareProtected(ZEN_MANAGE_DMD, 'setSendEventWhenBlockedFlag')
    def setSendEventWhenBlockedFlag(self):
        self.sendEventWhenBlockedFlag = True

    security.declareProtected(ZEN_MANAGE_DMD, 'unsetSendEventWhenBlockedFlag')
    def unsetSendEventWhenBlockedFlag(self):
        self.sendEventWhenBlockedFlag = False

    security.declareProtected(ZEN_MANAGE_DMD, 'unlock')
    def unlock(self, REQUEST=None):
        """Unlock object"""
        self.modelerLock = UNLOCKED
        self.unsetSendEventWhenBlockedFlag()

        if self.meta_type == 'Device':
            for dc in self.getDeviceComponents():
                dc.unlock()

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Unlocked',
                '%s has been unlocked.' % self.id
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'lockFromDeletion')
    def lockFromDeletion(self, sendEventWhenBlocked=None, REQUEST=None):
        """Lock object from being deleted"""
        self.modelerLock = DELETE_LOCKED
        if sendEventWhenBlocked:
            self.setSendEventWhenBlockedFlag()
        else:
            self.unsetSendEventWhenBlockedFlag()

        if self.meta_type == 'Device':
            for dc in self.getDeviceComponents():
                dc.lockFromDeletion(sendEventWhenBlocked)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Locked',
                '%s has been locked from deletion.' % self.id
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'lockFromUpdates')
    def lockFromUpdates(self, sendEventWhenBlocked=None, REQUEST=None):
        """Lock object from being deleted or updated"""
        self.modelerLock = UPDATE_LOCKED
        if sendEventWhenBlocked:
            self.setSendEventWhenBlockedFlag()
        else:
            self.unsetSendEventWhenBlockedFlag()

        if self.meta_type == 'Device':
            for dc in self.getDeviceComponents():
                dc.lockFromUpdates(sendEventWhenBlocked)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Locked',
                '%s has been locked from updates and deletion.' % self.id
            )
            return self.callZenScreen(REQUEST)

    def lockStatus(self):
        '''
        if self.modelerLock == DELETE_LOCKED:
            return "Locked from deletion"
        elif self.modelerLock == UPDATE_LOCKED:
            return "Locked from updates and deletion"
        elif isinstance(self.getPrimaryParent(), Lockable):
            return "%s by parent" % self.getPrimaryParent().lockStatus()
        elif self.modelerLock == UNLOCKED:
            return "Unlocked"
        '''
        if self.isLockedFromUpdates():
            return "locked from updates and deletion"
        elif self.isLockedFromDeletion():
            return "locked from deletion"
        else:
            return "unlocked"

    def lockWarning(self):
        if self.sendEventWhenBlocked():
            return "Send event when blocked"
        else:
            return "Do not send event when blocked"


InitializeClass(Lockable)
