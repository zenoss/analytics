##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Attribute, Interface

class IReportableFactory(Interface):
    def exports():
        """
        return an iterable of IReportables adapting the context
        """

class IReportable(Interface):
    id = Attribute("Identifier of the represented object (usually path)")
    uid = Attribute("The path in the object graph to the object")
    entity_class_name = Attribute("The name of the entity class, to be used" \
            + " when generating reporting schemas")

    def reportProperties():
        """
        get column values for entity. this is a list of tuples, where each
        contains the id, type, and value of the property
        """

class IReportableSubscriber(IReportable):
    """
    This type of IReportable is called from a factory that expects to get
    a list of subscribers.  In order to differentiate between a subscriber
    intended for factory A rather than from factory B, a factoryId is used.
    """
    zenpack = Attribute("ZenPack in which this subscriber lives.")
    factoryId = Attribute("Value used by factory to search for applicable reportables.")
