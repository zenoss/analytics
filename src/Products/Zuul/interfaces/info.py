##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Attribute
from Products.Zuul.interfaces import IMarshallable

class IInfo(IMarshallable):
    id = Attribute("Identifier of the represented object (usually path)")
    name = Attribute("Name of the represented object")
    uid = Attribute("The path in the object graph to the object")
