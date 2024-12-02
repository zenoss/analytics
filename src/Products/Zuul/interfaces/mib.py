##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode
from info import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IMibFacade(IFacade):

    def addMibPackage(self, package, organizer):
        """
        Add a MIB through whatever package type.
        Currently supports: tar, gzip, compress, URL
        """

    def getInfo(nodeId):
        """
        Get the MIBs tree by a mibTreeNodeId.
        """

    def moveMIBs(sourceUids, targetUid):
        """
        Move MIBOrganizers and MIBClasses uniquely identified by the
        sourceUids parameter to the MIBOrganizer uniquely identified by
        the targetUid parameter.
        """


class IMibOrganizerNode(ITreeNode):
    """
    Marker interface for providing a MIB organizer node in a MIB tree.
    """


class IMibNode(ITreeNode):
    """
    MIB node (trap or actual OID) in a MIB tree.
    """
    oid = Attribute('SNMP Object ID')


class IMibEntity(Interface):
    """
    Marker interface for MIBClass and MIBOrganizer
    """


class IMibNodeInfo(IInfo):
    """
    Represents a single OID Mapping instance.
    """
    name = schema.TextLine(title=_t(u'Name'),
                           description=_t(u'Name of this OID Mapping'))
    oid = schema.TextLine(title=_t(u'OID'),
                           description=_t(u'OID of this OID Mapping'))
    nodetype = schema.TextLine(title=_t(u'Nodetype'),
                           description=_t(u'Nodetype of this OID Mapping'))
    access = schema.TextLine(title=_t(u'Access'),
                           description=_t(u'Access of this OID Mapping'))
    status = schema.TextLine(title=_t(u'Status'),
                           description=_t(u'Status of this OID Mapping'))
    description = schema.Text(title=_t(u'Description'),
                           description=_t(u'Description of this OID Mapping'))

class IMibNotificationInfo(IInfo):
    """
    Represents a single Trap instance.
    """
    name = schema.TextLine(title=_t(u'Name'),
                           description=_t(u'Name of this Trap'))
    oid = schema.TextLine(title=_t(u'OID'),
                           description=_t(u'OID of this Trap'))
    nodetype = schema.TextLine(title=_t(u'Nodetype'),
                           description=_t(u'Nodetype of this Trap'))
    objects = schema.TextLine(title=_t(u'Objects'),
                           description=_t(u'Access of this Trap'))
    status = schema.TextLine(title=_t(u'Status'),
                           description=_t(u'Status of this Trap'))
    description = schema.Text(title=_t(u'Description'),
                           description=_t(u'Description of this Trap'))

class IMibInfo(IInfo):
    """
    Represents a single MIB instance.
    """
    newId = schema.TextLine(title=_t(u'Name'),
                        xtype="idfield",
                        required=True,
                        description=_t(u'The name of this MIB'))
    language = schema.TextLine(title=_t(u'Language'),
                           description=_t(u'Language of this MIB'))
    contact = schema.Text(title=_t(u'Contact'),
                           description=_t(u'Contact Info for this MIB'))
    description = schema.Text(title=_t(u'Description'),
                           description=_t(u'Description of this MIB'))


class IMibOrganizerInfo(IInfo):
    """
    Represents a single MibOrganizer instance.
    """
    name = Attribute('The name of the MIB')
    description = Attribute('A description of the MIB')
