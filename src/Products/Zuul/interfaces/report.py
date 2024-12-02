##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode

class IReportFacade(IFacade):
    pass

class IReportClassNode(ITreeNode):
    deletable = Attribute("can this node be deleted?")
    edit_url = Attribute("where can this node be edited?")

class IReportNode(ITreeNode):
    deletable = Attribute("can this node be deleted?")
    edit_url = Attribute("where can this node be edited?")
