##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import Interface
from Products.Zuul.interfaces import IInfo, IFacade, ITreeNode

class IEventClasses(Interface):
    """
    Marker interface for Event Classes.
    """

class IEventClassTreeNode(ITreeNode):
    """
    Marker interface for event class nodes in a tree.
    """

class IEventClassesFacade(IFacade):

    def addNewInstance(params=None):
        """
        Add new event class mapping for the current context
        @params.evclass = the event class this instance is associated with
        @params.instanceID = the instance ID
        """

    def editInstance(params=None):
        """
        edit an event class instance
        """

    def removeInstance(instances):
        """
        remove instance(s) from an event class
        @instances['context']
        @instances['id']
        """

    def getInstances(uid):
        """
        The all the instances mapped to this event class
        """

    def getInstanceData(uid):
        """
        return all extra data for instance id
        """
    def getSequence(uid):
        """
        returns the sequence order of keys for a given instance
        """
    def resequence(uids):
        """
        resequences a list of sequenced instances
        """

    def setTransform(uid, transform):
        """
        sets the transform for the context
        """

    def getTransform(uid):
        """
        returns a transform for the event class context
        """

    def getTransformTree(uid):
        """
        returns a transform for the event class context with all parent transforms
        """

    def isTransformEnabled(uid):
        """
        Returns True if transform is enabled, False if disabled.

        @uid The uid of effected event class
        """

    def setTransformEnabled(uid, enabled):
        """
        Enables or disables transform on the given event class.

        When disabled transform is enabled again, bad_transform events are cleared.

        @uid The uid of effected event class
        @enabled {boolean} Set True to enable transform, False to disable
        @returns True if transform is enabled, False if disabled
        """


    def editEventClassDescription(uid, description):
        """
        edit the description of a given event class
        """

    def testCompileTransform(transform):
        """Test our transform by compiling it.
        """

    def testRegex(regex, example):
        """Test our regex using the example event string.
        """

    def testRule(rule):
        """Test our rule by compiling it.
        """

    def moveInstance(targetUid, organizerUid):
        """
        move a mapped instance to a different organizer
        """

    def moveClassOrganizer(targetUid, organizerUid):
        """
        move an event class organizer under a different organizer
        """

    def getEventsCounts(uid):
        """
        return all the event counts for this context
        """

    def deleteEventClass(uid, id):
        """
        delete a selected entry
        """

class IEventClassInfo(IInfo):
    """
    Info object adapter for event classes
    """

