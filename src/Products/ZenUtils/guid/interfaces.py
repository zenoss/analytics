##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent


class IGloballyIdentifiable(Interface):
    """
    An object with a GUID.
    """
    def getPrimaryUrlPath():
        """
        The path under which the object can be found.
        """


class IGlobalIdentifier(Interface):
    """
    Adapter that manages GUID for objects.
    """
    def __init__(context):
        """
        Constructor
        """

    guid = Attribute("Globally unique identifier")

    def getGUID():
        """
        Gets the GUID associated with this object.
        """
    def setGUID(value):
        """
        Sets the GUID for this object.
        """
    def create(force):
        """
        Creates a new GUID and applies it to this object.
        """

class IGUIDManager(Interface):
    """
    A utility that can register objects as having guids and look up objects by
    guid.
    """
    def getPath(guid):
        """
        Return the path associated with a guid.
        """
    def getObject(guid):
        """
        Return the object associated with a guid.
        """
    def register(object):
        """
        Store the guid-path mapping in the reference table.
        """

class IGUIDEvent(IObjectEvent):
    pass
