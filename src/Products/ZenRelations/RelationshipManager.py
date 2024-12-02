##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """RelationshipManager

RelationshipManager is a mix in class to manage relationships
defined by the SchemaManager.
"""

from xml.sax import saxutils

import logging

import zope.interface
import zope.component

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from App.Management import Tabs
from App.special_dtml import DTMLFile
from OFS.interfaces import IItem

from Products.ZenModel.interfaces import IZenDocProvider
from Products.ZenUtils.Utils import unused

from .Exceptions import ZenSchemaError, zenmarker
from .PrimaryPathObjectManager import PrimaryPathObjectManager
from .RelSchema import RELMETATYPES
from .ZenPropertyManager import ZenPropertyManager

log = logging.getLogger("zen.Relations")


def manage_addRelationshipManager(context, id, title=None, REQUEST=None):
    """Relationship factory"""
    rm = RelationshipManager(id)
    context._setObject(id, rm)
    if REQUEST:
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )


addRelationshipManager = DTMLFile("dtml/addRelationshipManager", globals())


@zope.interface.implementer(IItem)
class RelationshipManager(PrimaryPathObjectManager, ZenPropertyManager):
    """
    RelationshipManger is an ObjectManager like class that can contain
    relationships (in fact relationships can only be added to a
    RelationshipManager).

    Relationships are defined on an RM by the hash _relations.  It
    should be defined on the class so that it isn't stored in the database.
    If there is inheritance involved remember to add the base class _relations
    definition to the current class so that all relationships for the class
    are defined on it.

    remoteClassStr - is a string that represents the full path to the remote
                    class.  Its a string because in most cases the classes
                    will be in different modules which would cause a recursive
                    import of the two modules.

    _relations = (
        ("toonename", ToOne(ToMany, remoteClassStr, remoteName)),
        ("tomanyname", ToMany(ToMany, remoteClassStr, remoteName)),
        )
    """

    _relations = ()

    meta_type = "Relationship Manager"

    security = ClassSecurityInfo()

    manage_options = (
        PrimaryPathObjectManager.manage_options
        + ZenPropertyManager.manage_options
    )

    manage_main = DTMLFile("dtml/RelationshipManagerMain", globals())

    # are we being deleted or moved
    _operation = -1

    def __init__(self, id, title=None, buildRelations=True):
        unused(title)
        self.id = id
        if buildRelations:
            self.buildRelations()

    def getRelationshipManagerId(self):
        """
        Return our simple id if we are called from our primary path
        else return the full primary id.
        """
        if self.getPhysicalPath() == self.getPrimaryPath():
            return self.id
        return self.getPrimaryId()

    ##########################################################################
    #
    # Methods for relationship management.
    #
    ##########################################################################

    def addRelation(self, name, obj):
        """Form a bi-directional relationship."""
        rel = getattr(self, name, None)
        if rel is None:
            raise AttributeError("Relationship %s, not found" % name)
        rel.addRelation(obj)

    def removeRelation(self, name, obj=None, suppress_events=False):
        """
        Remove an object from a relationship.
        If no object is passed all objects are removed.
        """
        rel = getattr(self, name, None)
        if rel is None:
            raise AttributeError("Relationship %s, not found" % name)
        rel.removeRelation(obj, suppress_events=suppress_events)

    def _setObject(self, id, object, roles=None, user=None, set_owner=1):
        if object.meta_type in RELMETATYPES:
            schema = self.lookupSchema(id)
            if not schema.checkType(object):
                raise ZenSchemaError(
                    "Relationship %s type %s != %s"
                    % (id, object.meta_type, schema.__class__.__name__)
                )
        return PrimaryPathObjectManager._setObject(
            self, id, object, roles, user, set_owner
        )

    ##########################################################################
    #
    # Methods for copy management
    #
    ##########################################################################

    def _getCopy(self, container):
        """
        Create a copy of this relationship manager.  This involes copying
        relationships and removing invalid relations (ie ones with ToOne)
        and performing copies of any contained objects.
        Properties are also set on the new object.
        """
        id = self.id
        if getattr(aq_base(container), id, zenmarker) is not zenmarker:
            id = "copy_of_" + id
        cobj = self.__class__(id, buildRelations=False)  # make new instance
        cobj = cobj.__of__(container)  # give the copy container's aq chain
        for objid, sobj in self.objectItems():
            # if getattr(aq_base(self), objid, None): continue
            csobj = sobj._getCopy(cobj)
            cobj._setObject(csobj.id, csobj)
        for name, value in self.propertyItems():
            cobj._updateProperty(name, value)
        return aq_base(cobj)

    def _notifyOfCopyTo(self, container, op=0):
        """Manage copy/move/rename state for use in manage_beforeDelete."""
        unused(container)
        self._operation = op  # 0 == copy, 1 == move, 2 == rename

    def cb_isMoveable(self):
        """Prevent move unless we are being called from our primary path."""
        if self.getPhysicalPath() == self.getPrimaryPath():
            return PrimaryPathObjectManager.cb_isMoveable(self)
        return 0

    def moveMeBetweenRels(self, srcRelationship, destRelationship):
        """
        Move a relationship manager without deleting its relationships.
        """
        self._operation = 1
        srcRelationship._delObject(self.id)
        self = aq_base(self)
        destRelationship._setObject(self.id, self)
        return destRelationship._getOb(self.id)

    def moveObject(self, obj, destination):
        """
        Move obj from this RM to the destination RM
        """
        self._operation = 1
        self._delObject(obj.id)
        obj = aq_base(obj)
        destination._setObject(obj.id, obj)
        return destination._getOb(obj.id)

    ##########################################################################
    #
    # Functions for examining a RelationshipManager's schema
    #
    ##########################################################################

    def buildRelations(self):
        """build our relations based on the schema defined in _relations"""
        if not getattr(self, "_relations", False):
            return
        relnames = self.getRelationshipNames()
        for name, schema in self._relations:
            if name not in relnames:
                self._setObject(name, schema.createRelation(name))
            if name in relnames:
                relnames.remove(name)
        for rname in relnames:
            self._delObject(rname)

    def lookupSchema(cls, relname):
        """
        Lookup the schema definition for a relationship.
        All base classes are checked until RelationshipManager is found.
        """
        for name, schema in cls._relations:
            if name == relname:
                return schema
        raise ZenSchemaError(
            "Schema for relation %s not found on %s" % (relname, cls.__name__)
        )

    lookupSchema = classmethod(lookupSchema)

    def getRelationships(self):
        """Returns a dictionary of relationship objects keyed by their names"""
        return self.objectValues(spec=RELMETATYPES)

    def getRelationshipNames(self):
        """Return our relationship names"""
        return self.objectIds(spec=RELMETATYPES)

    def checkRelations(self, repair=False):
        """Confirm the integrity of all relations on this object"""
        log.debug("checking relations on object %s", self.getPrimaryId())
        for rel in self.getRelationships():
            rel.checkRelation(repair)

    ##########################################################################
    #
    # Functions for exporting RelationshipManager to XML
    #
    ##########################################################################

    def exportXml(
        self,
        ofile,
        ignorerels=[],
        root=False,
        exportPasswords=False,
        move=False,
    ):
        """Return an xml based representation of a RelationshipManager
        <object id='/Devices/Servers/Windows/dhcp160.confmon.loc'
            module='Products.Confmon.IpInterface' class='IpInterface'>
            <property id='name'>jim</property>
            <toone></toone>
            <tomany></tomany>
            <tomanycont></tomanycont>
        </object>
        """
        modname = self.__class__.__module__
        classname = self.__class__.__name__
        id = root and self.getPrimaryId() or self.id
        stag = "<object id='%s' module='%s' class='%s' move='%s'>\n" % (
            id,
            modname,
            classname,
            move,
        )
        ofile.write(stag)
        zendocAdapter = zope.component.queryAdapter(self, IZenDocProvider)
        if zendocAdapter is not None:
            zendocAdapter.exportZendoc(ofile)
        self.exportXmlProperties(ofile, exportPasswords)
        self.exportXmlRelationships(ofile, ignorerels)

        try:
            self.exportProdState(ofile)
        except AttributeError:
            pass

        exportHook = getattr(aq_base(self), "exportXmlHook", None)
        if exportHook and callable(exportHook):
            self.exportXmlHook(ofile, ignorerels)
        ofile.write("</object>\n")

    def exportProdState(self, ofile):
        stag = (
            "<property id='prodstate' mode='w' type='string'>%s</property>"
            % (self.getProductionState())
        )
        ofile.write(stag)

    def exportXmlProperties(self, ofile, exportPasswords=False):
        """Return an xml representation of a RelationshipManagers properties
        <property id='name' type='type' mode='w' select_variable='selectvar'>
            value
        </property>
        value will be converted to is correct python type on import
        """
        for prop in self._properties:
            if "id" not in prop:
                continue
            id = prop["id"]
            ptype = prop["type"]
            value = getattr(aq_base(self), id, None)  # use aq_base?
            if not value:
                if ptype in ("string", "text", "password"):
                    if not id.startswith("z"):
                        continue
                elif ptype == "lines":
                    if value is None:
                        continue
                elif ptype not in ("int", "float", "boolean", "long"):
                    continue
            if ptype == "password" and not exportPasswords:
                value = ""
            stag = []
            stag.append("<property")
            for k, v in prop.items():
                if ptype != "selection" and k == "select_variable":
                    continue
                v = saxutils.quoteattr(str(v))
                stag.append("%s=%s" % (k, v))
            stag.append(">")
            ofile.write(" ".join(stag) + "\n")
            if not isinstance(value, basestring):
                value = unicode(value)
            elif isinstance(value, str):
                value = value.decode("latin-1")
            valuestr = saxutils.escape(value).encode("utf-8").strip()
            if valuestr:
                ofile.write(valuestr + "\n")
            ofile.write("</property>\n")

    def exportXmlRelationships(self, ofile, ignorerels=[]):
        """Return an xml representation of Relationships"""
        for rel in self.getRelationships():
            if rel.id in ignorerels:
                continue
            rel.exportXml(ofile, ignorerels)

    ##########################################################################
    #
    # Methods called from UI code.
    #
    ##########################################################################

    security.declareProtected("Manage Relations", "manage_addRelation")

    def manage_addRelation(self, name, obj, REQUEST=None):
        """make a relationship"""
        self.addRelation(name, obj)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    security.declareProtected("Manage Relations", "manage_removeRelation")

    def manage_removeRelation(self, name, id=None, REQUEST=None):
        """remove a relationship to be called from UI"""
        rel = getattr(self, name, None)
        if rel is None:
            raise AttributeError("Relationship %s, not found" % name)
        rel._delObject(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def manage_workspace(self, REQUEST):
        """return the workspace of the related object using its primary path"""
        url = REQUEST["URL"]
        myp = self.getPrimaryUrlPath()
        if url.find(myp) > 0:
            Tabs.manage_workspace(self, REQUEST)
        else:
            from zExceptions import Redirect

            raise Redirect(myp + "/manage_workspace")


InitializeClass(RelationshipManager)
