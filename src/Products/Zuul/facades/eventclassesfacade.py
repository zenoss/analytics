##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re
import sre_constants
import logging
log = logging.getLogger('zen.EventClassesFacade')

from zope.interface import implements
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IEventClassesFacade, IEventClassInfo, IInfo
from Products.ZenEvents import EventClass
from Acquisition import aq_parent

class EventClassesFacade(TreeFacade):
    implements(IEventClassesFacade)

    def addNewInstance(self, params=None):
        """
        Add new event class mapping for the current context
        @params.evclass = the event class this instance is associated with
        @params.instanceID = the instance ID
        """
        obj = self._getObject(params['evclass'])
        result = IInfo(obj.createInstance(params['newName']))
        return result

    def editInstance(self, params=None):
        """
        edit an event class instance
        """
        obj = self._getObject(params['uid'])

        if obj.eventClassKey != params['eventClassKey']:
            obj.unindex_object()
            obj.sequence = obj.eventClass().nextSequenceNumber(params['eventClassKey'])
            obj.eventClassKey = params['eventClassKey']
            obj.index_object()

        obj.rule = params['rule']
        obj.regex = params['regex']
        obj.example = params['example']
        obj.explanation = params['explanation']
        obj.resolution = params['resolution']
        obj.transform = params.get('transform', obj.transform)

        if params['instanceName'] != params['newName']:
            obj.rename(params['newName'])

    def removeInstance(self, instances):
        """
        remove instance(s) from an event class
        @instances['context']
        @instances['id']
        """
        for entry in instances:
            obj = self._getObject(entry['context'])
            obj.instances._delObject(entry['id'])

    def getInstances(self, uid):
        """
        The all the instances mapped to this event class
        """
        obj = self._getObject(uid)
        instances = [IInfo(i) for i in obj.getInstances()]
        inst = []
        for entry in instances:
            hasTrans = True if entry.transform else False
            inst.append({
                            'hasTransform': hasTrans,
                            'id': entry.id,
                            'uid':entry.uid,
                            'eventClassKey': entry.eventClassKey,
                            'eval': entry.example
                        })
        return inst

    def getInstanceData(self, uid):
        """
        return all extra data for instance id
        """
        obj = self._getObject(uid)
        inst = [{
            'id':obj.id,
            'uid':uid,
            'eventClass':obj.eventClass().id,
            'eventClassKey':obj.eventClassKey,
            'rule':obj.rule,
            'regex':obj.regex,
            'sequence':obj.sequence,
            'evaluation':obj.explanation,
            'example':obj.example,
            'resolution':obj.resolution,
            'transform':obj.transform
        }]
        return inst


    def getSequence(self, uid):
        """
        returns the sequence order of keys for a given instance
        """
        obj = self._getObject(uid)
        seq = obj.sameKey()
        sequences = []
        for i, entry in enumerate(seq):
            sequences.append({
                'id': entry.id,
                'uid':entry.getPrimaryUrlPath(),
                'eventClass':entry.eventClass().id,
                'eventClassKey':entry.eventClassKey,
                'sequence':i,
                'eval':entry.ruleOrRegex()
            })
        return sequences

    def resequence(self, uids):
        """
        resequences a list of sequenced instances
        """
        for i, uid in enumerate(uids):
            obj = self._getObject(uid.replace("%20", " "))
            obj.sequence = i

    def setTransform(self, uid, transform):
        """
        sets the transform for the context
        """
        obj = self._getObject(uid)
        obj.transform = transform

    def getTransform(self, uid):
        """
        returns a transform for the event class context
        """
        obj = self._getObject(uid)
        return obj.transform

    def getTransformTree(self, uid):
        """
        returns a transform for the event class context with all parent transforms
        """
        object = self._getObject(uid)

        transpath = object._eventClassPath()
        transforms = []
        for obj in transpath:
            if not obj.transform: continue
            if obj.transform == object.transform: break
            transforms.append({
                'transid'   : obj.getPrimaryDmdId(),
                'trans'     : obj.transform
            })
        transforms.append({
            'transid': object.getPrimaryDmdId(),
            'trans'  : object.transform
        })
        return transforms

    def isTransformEnabled(self, uid):
        """
        Returns True if transform is enabled, False if disabled.
        """
        obj = self._getObject(uid)
        return obj.transformEnabled

    def setTransformEnabled(self, uid, enabled):
        """
        Enables or disables transforms on the given event class.
        When disabled transforms are enabled again, bad_transform events are cleared.
        """
        obj = self._getObject(uid)
        obj.transformEnabled = bool(enabled)

        if obj.transformEnabled:
            # clear events about disabled transform
            zem = self._dmd.ZenEventManager
            prefix = '/zport/dmd/Events'
            if uid.startswith(prefix):
                eventclass_name = uid[len(prefix):]
            else:
                eventclass_name = uid
            evt = dict(
                summary='Clear event about failed/disabled transform.',
                eventClass='/App/Zenoss',
                eventKey='transform_failed',
                device=zem.host,
                severity=0,
                component=eventclass_name
            )
            zem.sendEvent(evt)
            evt['eventKey'] = 'transform_disabled'
            zem.sendEvent(evt)
        return obj.transformEnabled

    def editEventClassDescription(self, uid, description):
        """
        edit the description of a given event class
        """
        obj = self._getObject(uid)
        obj.description = description

    def testCompileTransform(self, transform):
        """Test our transform by compiling it.
        """
        if transform:
            compile(transform, "<string>", "exec")

    def testRegex(self, regex, example):
        """Test our regex using the example event string.
        """
        if not regex:
            return False
        if not example:
            return False
        try:
            value = re.search(regex, example, re.I)
            if not value: return "Regex and Example do not match"
        except sre_constants.error:
            return sre_constants.error
        return True

    def testRule(self, rule):
        """Test our rule by compiling it.
        """
        if not rule:
            return False
        compile(rule, "<string>", "eval")

    def moveInstance(self, targetUid, organizerUid):
        """
        move a mapped instance to a different organizer
        """
        object2bmoved = self._getObject(organizerUid)
        parent = aq_parent(aq_parent(object2bmoved))
        target = self._getObject(targetUid)
        parent.moveInstances(target.getOrganizerName(), [object2bmoved.id])

    def moveClassOrganizer(self, targetUid, organizerUid):
        """
        move an event class organizer under a different organizer
        """
        organizer = self._getObject(organizerUid)
        parent = organizer.getPrimaryParent()
        parent.moveOrganizer(targetUid, [organizer.id])
        # reindex all the instances under the organizer
        for inst in parent.getInstances():
            inst.index_object()

    def getEventsCounts(self, uid):
        """
        return all the event counts for this context
        """
        obj = self._getObject(uid)
        return obj.getEventSeveritiesCount()
