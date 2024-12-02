##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface
from Products.Zuul.interfaces import IFacade

class IProperties(Interface):
    """
    Marker interface for Properties. 
    """

class IPropertiesFacade(IFacade): 

    def getZenProperties(self, uid, start, params, limit, sort, page, dir):
        """
        Returns the definition and values of all
        the zen properties for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
            
    def getZenProperty(self, uid, zProperty):
        """
        Returns information about a zproperty for a
        given context, including its value
        @rtype:   Dictionary
        @return:  B{Properties}:
             - path: (string) where the property is defined
             - type: (string) type of zproperty it is
             - options: (Array) available options for the zproperty
             - value (Array) value of the zproperty
             - valueAsString (string)
        """     
        
    def getCustomProperties(self, uid, start, param, limit, sort, page, dir):
        """
        Returns the definition and values of all
        the zen properties for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """  
        
    def addCustomProperty(self, id, value, label, uid, type):
        """
        adds a new property to the / of the tree
        """

    def setZenProperty(self, uid, zProperty, value):
        """
        Sets the zProperty or cProperty value  
        """
        
    def deleteZenProperty(self, uid, zProperty):
        """
        Removes the local instance of the each property in properties. Note
        that the property will only be deleted if a hasProperty is true
        * also used on custom properties or cProperties
        @type  uid: String
        @param uid: unique identifier of an object
        @type  properties: String
        @param properties: zenproperty identifier
        """

    
    
