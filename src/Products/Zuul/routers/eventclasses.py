##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.EventClasses")

from Products.ZenUtils.Ext import DirectResponse
from Products import Zuul
from Products.Zuul.decorators import require, serviceConnectionError
from Products.Zuul.routers import TreeRouter
from Products.ZenMessaging.audit import audit
from collections import Mapping


class EventClassesRouter(TreeRouter):
    """
    Event Classes and their instance maps
    """

    def _getFacade(self):
        return Zuul.getFacade('eventclasses', self.context)

    @serviceConnectionError
    def addNewInstance(self, params=None):
        """
        Add new event class mapping for the current context
        """
        facade = self._getFacade()
        newInstance = facade.addNewInstance(params)
        audit('UI.EventClasses.AddInstance', params['newName'], data_=params)
        return DirectResponse.succeed(data=Zuul.marshal(newInstance))
        
    @require('Manage DMD')
    def removeInstance(self, instances):
        """
        remove instance(s) from an event class
        """
        facade = self._getFacade()
        facade.removeInstance(instances)
        audit('UI.EventClasses.RemoveInstances', instance=instances)        
        return DirectResponse.succeed()

    @serviceConnectionError        
    @require('Manage DMD')    
    def editInstance(self, params=None):
        """
        Edit an event class instance
        """
        oldData = self.getInstanceData(params['uid']).data
        self.testCompileTransform(params.get('transform'))
        self.testRegex(params['regex'], params['example'])
        self.testRule(params['rule'])
        facade = self._getFacade()
        facade.editInstance(params)

        audit('UI.EventClasses.EditInstance', params['uid'],
              data_=params, oldData_=oldData)

        return DirectResponse.succeed()

    @serviceConnectionError
    def getInstances(self, uid, params=None):
        """
        Returns event class mappings for the current context
        """
        facade = self._getFacade()
        data = facade.getInstances(uid)

        return DirectResponse( data=Zuul.marshal(data) )

    @serviceConnectionError
    def getInstanceData(self, uid):
        """
        return all extra data for instance id
        """
        facade = self._getFacade()
        data = facade.getInstanceData(uid)
        return DirectResponse(data=Zuul.marshal(data) )

    def getSequence(self, uid):
        """
        returns the sequence order of keys for a given instance
        """
        facade = self._getFacade()
        data = facade.getSequence(uid)        
        return DirectResponse(data=Zuul.marshal(data) )
        
    @require('Manage DMD')
    def resequence(self, uids):
        """
        resequences a list of sequenced instances
        """
        facade = self._getFacade()
        facade.resequence(uids)
        audit('UI.EventClasses.Resequence', sequence=uids)        
        return DirectResponse.succeed()

    def setTransform(self, uid, transform):
        """
        sets the transform for the context
        """
        self.testCompileTransform(transform)
        facade = self._getFacade()
        facade.setTransform(uid, transform)
        if isinstance(transform, Mapping):
            auditTransform = transform
        else:
            auditTransform = {'transform': transform}
        audit('UI.EventClasses.SetTransform', uid, data_=auditTransform)
        return DirectResponse.succeed()

    def getTransform(self, uid):
        """
        returns a transform for the context
        """
        facade = self._getFacade()
        data = facade.getTransform(uid)
        return DirectResponse(data=Zuul.marshal(data) )

    def getTransformTree(self, uid):
        """
        returns a transform for the context with all its inherited transforms
        """
        facade = self._getFacade()
        data = facade.getTransformTree(uid)
        return DirectResponse(data=Zuul.marshal(data) )

    def isTransformEnabled(self, uid):
        """
        Returns True if transform is enabled, False if disabled.
        """
        facade = self._getFacade()
        data = facade.isTransformEnabled(uid)
        return DirectResponse(data=Zuul.marshal(data) )

    @require('Manage DMD')
    def setTransformEnabled(self, uid, enabled):
        """
        Enables or disables transforms on the given event class.
        When disabled transforms are enabled again, bad_transform events are cleared.
        """
        facade = self._getFacade()
        data = facade.setTransformEnabled(uid, enabled)
        return DirectResponse(data=Zuul.marshal(data) )

    @require('Manage DMD')
    def editEventClassDescription(self, uid, description):
        """
        edit the description of a given event class
        """
        facade = self._getFacade()
        facade.editEventClassDescription(uid, description)
        audit('UI.EventClasses.EditEventClass', EventClass=uid, Description=description)        
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def deleteEventClass(self, uid, params=None):
        """
        remove an event class
        """
        facade = self._getFacade()
        facade.deleteNode(uid)
        audit('UI.EventClasses.DeleteEventClass', deletedEventClass=uid) 
        return DirectResponse.succeed()

    def testCompileTransform(self, transform):
        """
        Test our transform by compiling it.
        """
        facade = self._getFacade()
        facade.testCompileTransform(transform)
        return DirectResponse.succeed()

    def testRegex(self, regex, example):
        """
        Test our regex using the example event string.
        """
        facade = self._getFacade()
        reg = facade.testRegex(regex, example)
        if reg is True:
            return DirectResponse.succeed()
        return DirectResponse.fail(reg)

    def testRule(self, rule):
        """
        Test our rule by compiling it.
        """
        facade = self._getFacade()
        facade.testRule(rule)
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def moveInstance(self, params):
        """
        move a mapped instance to a different organizer
        @params['targetUid']
        @params['UidsToMove']
        """
        facade = self._getFacade()
        for uid in params['UidsToMove']:
            facade.moveInstance(params['targetUid'], uid)
        audit('UI.EventClasses.MoveInstance', movedInstances=params['UidsToMove'], target=params['targetUid'])            
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def moveClassOrganizer(self, params):
        """
        move an event class organizer under a different organizer
        """
        facade = self._getFacade()
        facade.moveClassOrganizer(params['targetUid'], params['UidsToMove'][0])
        audit('UI.EventClasses.MoveOrganizer', movedOrganizer=params['UidsToMove'], target=params['targetUid'])                    
        return DirectResponse.succeed()

    def getEventsCounts(self, uid):
        """
        return all the event counts for this context
        """
        facade = self._getFacade()
        data = facade.getEventsCounts(uid)
        return DirectResponse(data=Zuul.marshal(data) )
