##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ImportRM
Import RelationshipManager objects into a Zope database
This provides support methods used by the Python xml.sax library to
parse and construct an XML document.

Descriptions of the XML document format can be found in the
Developers Guide.
"""

from __future__ import absolute_import

import os
import sys

from xml.sax import make_parser, saxutils, SAXParseException
from xml.sax.handler import ContentHandler

import six
import transaction
import zope.component

from Acquisition import aq_base
from DateTime import DateTime
from zExceptions import NotFound
from zope.event import notify

from Products.ZenModel.interfaces import IZenDocProvider
from Products.ZenUtils.Utils import importClass, getObjByPath, getObjByPath2
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.Zuul.catalog.events import IndexingEvent

_STRING_PROPERTY_TYPES = ("string", "text", "password")


class ImportRM(ZCmdBase, ContentHandler):
    """
    Wrapper module to interface between Zope and the Python SAX XML library.
    The xml.sax.parse() calls different routines depending on what it finds.

    A simple example of a valid XML file can be found in the objects.xml file
    for a ZenPack.

    <?xml version="1.0"?>
    <objects>
      <!-- ('', 'zport', 'dmd', 'Devices', 'rrdTemplates', 'HelloWorld') -->
      <object
        id='/zport/dmd/Devices/rrdTemplates/HelloWorld'
        module='Products.ZenModel.RRDTemplate'
        class='RRDTemplate'>
        <property type="text" id="description" mode="w">
          This is the glorious description that shows up when we click
          on our RRD template
        </property>
        <tomanycont id='datasources'>
          <object
            id='hello'
            module='Products.ZenModel.BasicDataSource'
            class='BasicDataSource'>
            <property
              select_variable="sourcetypes"
              type="selection"
              id="sourcetype"
              mode="w">SNMP</property>
            <property
              type="boolean" id="enabled" mode="w">True</property>
            <property
              type="string" id="eventClass" mode="w">/Cmd/Fail</property>
            <property
              type="int" id="severity" mode="w">3</property>
            <property type="int" id="cycletime" mode="w">300</property>
            <property type="boolean" id="usessh" mode="w">False</property>
            <tomanycont id='datapoints'>
              <object
                id='hello'
                module='Products.ZenModel.RRDDataPoint'
                class='RRDDataPoint'>
                <property
                  select_variable="rrdtypes"
                  type="selection"
                  id="rrdtype"
                  mode="w">GAUGE</property>
                <property
                  type="boolean" id="isrow" mode="w">True</property>
              </object>
            </tomanycont>
          </object>

    <!--    snip  -->

    </objects>
    """

    rootpath = ""
    skipobj = 0

    def __init__(self, noopts=0, app=None, keeproot=False):
        """
        Initializer

        @param noopts: don't use sys.argv for command-line options
        @type noopts: boolean
        @param app: app
        @type app: object
        @param keeproot: keeproot
        @type keeproot: boolean
        """
        ZCmdBase.__init__(self, noopts, app, keeproot)
        ContentHandler.__init__(self)

    def context(self):
        """
        Return the bottom object in the stack

        @return:
        @rtype: object
        """
        return self.objstack[-1]

    def cleanattrs(self, attrs):
        """
        Convert all attributes to string values

        @param attrs: (key,val) pairs
        @type attrs: list
        @return: same list, but with all values as strings
        @rtype: list
        """
        myattrs = {}
        for key, val in attrs.items():
            myattrs[key] = str(val)
        return myattrs

    def startElement(self, name, attrs):
        """
        Function called when the parser finds the starting element
        in the XML file.

        @param name: name of the element
        @type name: string
        @param attrs: list of (key, value) tuples
        @type attrs: list
        """
        ignoredElements = ["objects"]
        attrs = self.cleanattrs(attrs)
        if self.skipobj > 0:
            self.skipobj += 1
            return

        self.log.debug(
            "tag %s, context %s, line %s",
            name,
            self.context().id,
            self._locator.getLineNumber(),
        )

        if name == "object":
            if attrs.get("class") == "Device" and not attrs.get("move", False):
                devId = attrs["id"].split("/")[-1]
                dev = self.dmd.Devices.findDeviceByIdOrIp(devId)
                if dev:
                    msg = (
                        "The device %s already exists on this system! "
                        "(Line %s)" % (devId, self._locator.getLineNumber())
                    )
                    raise Exception(msg)

            if attrs.get("class") == "IpAddress":
                ipAddress = attrs["id"]
                dev = self.dmd.Devices.findDeviceByIdOrIp(ipAddress)
                if dev:
                    msg = (
                        "The IP address %s already exists on this system! "
                        "(Line %s)"
                        % (ipAddress, self._locator.getLineNumber())
                    )
                    raise Exception(msg)

            obj = self.createObject(attrs)
            if obj is None:
                formattedAttrs = ""
                for key, value in attrs.items():
                    formattedAttrs += "  * %s: %s\n" % (key, value)
                raise Exception(
                    "Unable to create object using the following "
                    "attributes:\n%s" % formattedAttrs
                )

            if (
                not self.options.noindex
                and hasattr(aq_base(obj), "reIndex")
                and not self.rootpath
            ):
                self.rootpath = obj.getPrimaryId()

            self.objstack.append(obj)

        elif name == "tomanycont" or name == "tomany":
            nextobj = self.context()._getOb(attrs["id"], None)
            if nextobj is None:
                self.skipobj = 1
                return
            else:
                self.objstack.append(nextobj)
        elif name == "toone":
            relname = attrs.get("id")
            self.log.debug(
                "toone %s, on object %s", relname, self.context().id
            )
            rel = getattr(aq_base(self.context()), relname, None)
            if rel is None:
                return
            objid = attrs.get("objid")
            self.addLink(rel, objid)
        elif name == "link":
            self.addLink(self.context(), attrs["objid"])
        elif name == "property":
            self.curattrs = attrs
        elif name in ignoredElements:
            pass
        else:
            self.log.warning("Ignoring an unknown XML element type: %s", name)

    def _ensureUniqueOID(self, node):
        # Removes MibNode/MibNotification objects that have the same 'oid'
        # value as the given 'node' object but are contained by a different
        # MibModule object.
        for brain in self.dmd.Mibs.mibSearch(oid=node.oid):
            try:
                indexed_node = brain.getObject()
                # Equal moduleName values means that index_node and node
                # are (probably) the same object.
                if indexed_node.moduleName == node.moduleName:
                    continue
            except KeyError as ex:
                self.log.warn(
                    "Invalid catalog entry; path '%s': %s", brain.getPath(), ex
                )
            else:
                self.log.debug(
                    "OID '%s' will be removed from organizer '%s' "
                    "and added to organizer '%s'.",
                    node.oid,
                    indexed_node.moduleName,
                    node.moduleName,
                )
                indexed_node.getParentNode()._delObject(indexed_node.id)

    def endElement(self, name):
        """
        Function called when the parser finds the starting element
        in the XML file.

        @param name: name of the ending element
        @type name: string
        """
        ignoredElements = ["toone", "link"]
        if self.skipobj > 0:
            self.skipobj -= 1
            return

        noIncrementalCommit = (
            self.options.noCommit or self.options.chunk_size == 0
        )

        if name in ("object", "tomany", "tomanycont"):
            obj = self.objstack.pop()
            if obj.getNodeName() in ("MibNode", "MibNotification"):
                self._ensureUniqueOID(obj)

            notify(IndexingEvent(obj))
            if hasattr(aq_base(obj), "index_object"):
                obj.index_object()
            if self.rootpath == obj.getPrimaryId():
                self.log.info("Calling reIndex %s", obj.getPrimaryId())
                obj.reIndex()
                self.rootpath = ""

            # Not committing, or no objects to commit.
            if noIncrementalCommit or not self.uncommittedObjects:
                return

            # Commit only after "chunk_size" objects need committed.
            if self.uncommittedObjects >= self.options.chunk_size:
                self.log.debug(
                    "Committing a batch of %s objects", self.options.chunk_size
                )
                self.commit()

        elif name == "objects":  # ie end of the file
            self.log.info("End loading objects")
            self.log.info("Processing links")
            self.processLinks()
            if not self.options.noCommit:
                self.commit()
                self.log.info(
                    "Loaded %d objects into the ZODB database",
                    self.objectnumber,
                )
            else:
                self.log.info(
                    "Would have created %d objects in the ZODB database",
                    self.objectnumber,
                )

        elif name == "property":
            if self.curattrs["id"] == "prodstate":
                prodState = int(self.charvalue)
                self.context().setProdState(prodState)
            else:
                self.setProperty(self.context(), self.curattrs, self.charvalue)

            # We've closed off a tag, so now we need to re-initialize
            # the area that stores the contents of elements
            self.charvalue = ""

        elif name in ignoredElements:
            pass
        else:
            self.log.warning("Ignoring an unknown XML element type: %s", name)

    def characters(self, chars):
        """
        Called by xml.sax.parse() with data found in an element
        eg <object>my characters stuff</object>

        Note that this can be called character by character.

        @param chars: chars
        @type chars: string
        """
        self.charvalue += saxutils.unescape(chars)

    def createObject(self, attrs):
        """
        Create an object and set it into its container

        @param attrs: attrs
        @type attrs: string
        @return: newly created object
        @rtype: object
        """
        # Does the object exist already?
        id = attrs.get("id")
        obj = None
        try:
            if id.startswith("/"):
                obj = getObjByPath2(self.app, id)
            else:
                obj = self.context()._getOb(id)
        except (KeyError, AttributeError, NotFound):
            pass

        if obj is None:
            klass = importClass(attrs.get("module"), attrs.get("class"))
            if id.find("/") > -1:
                (contextpath, id) = os.path.split(id)
                try:
                    pathobj = getObjByPath(self.context(), contextpath)
                except (KeyError, AttributeError, NotFound):
                    self.log.warn(
                        "Unable to find context path %s (line %s ?) for %s",
                        contextpath,
                        self._locator.getLineNumber(),
                        id,
                    )
                    if not self.options.noCommit:
                        self.log.warn("Not committing any changes")
                        self.options.noCommit = True
                    return None
                self.objstack.append(pathobj)
            self.log.debug(
                "Building instance %s of class %s", id, klass.__name__
            )
            try:
                if klass.__name__ == "AdministrativeRole":
                    user = [
                        x
                        for x in self.dmd.ZenUsers.objectValues()
                        if x.id == id
                    ]
                    if user:
                        obj = klass(user[0], self.context().device())
                    else:
                        msg = "No AdminRole user %s exists (line %s)" % (
                            id,
                            self._locator.getLineNumber(),
                        )
                        self.log.error(msg)
                        raise Exception(msg)
                else:
                    obj = klass(id)
            except TypeError:
                # This happens when the constructor expects more arguments
                self.log.exception(
                    "Unable to build %s instance of class %s (line %s)",
                    id,
                    klass.__name__,
                    self._locator.getLineNumber(),
                )
                raise
            self.context()._setObject(obj.id, obj)
            obj = self.context()._getOb(obj.id)
            self.objectnumber += 1
            self.uncommittedObjects += 1
            self.log.debug("Added object %s to database", obj.getPrimaryId())
        else:
            self.log.debug("Object %s already exists -- skipping", id)
        return obj

    def setZendoc(self, obj, value):
        zendocObj = zope.component.queryAdapter(obj, IZenDocProvider)
        if zendocObj is not None:
            zendocObj.setZendoc(value)
        elif value:
            self.log.warn(
                "zendoc property could not be set to" " %s on object %s",
                value,
                obj.id,
            )

    def setProperty(self, obj, attrs, value):
        """
        Set the value of a property on an object.

        @param obj: obj
        @type obj: string
        @param attrs: attrs
        @type attrs: string
        @param value: value
        @type value: string
        @return:
        @rtype:
        """
        name = attrs.get("id")
        proptype = attrs.get("type")
        setter = attrs.get("setter", None)
        self.log.debug(
            "Setting object %s attr %s type %s value %s",
            obj.id,
            name,
            proptype,
            value,
        )
        linenum = self._locator.getLineNumber()

        # Sanity check the value
        value = value.strip()
        try:
            value = str(value)
        except UnicodeEncodeError as ex:
            self.log.warn(
                "UnicodeEncodeError at line %s  "
                "object-id=%s attribute=%s property-type=%s error=%s",
                linenum,
                obj.id,
                name,
                proptype,
                ex,
            )

        if name == "zendoc":
            return self.setZendoc(obj, value)

        # Guess at how to interpret the value given the property type
        if proptype == "selection":
            try:
                firstElement = getattr(obj, name)[0]
                if isinstance(firstElement, six.string_types):
                    proptype = "string"
            except (TypeError, IndexError) as ex:
                self.log.warn(
                    "Error at line %s  "
                    "object-id=%s attribute=%s property-type=%s error=%s",
                    linenum,
                    obj.id,
                    name,
                    proptype,
                    ex,
                )
                proptype = "string"

        if proptype == "date":
            try:
                value = float(value)
            except ValueError:
                pass
            value = DateTime(value)

        elif proptype not in _STRING_PROPERTY_TYPES:
            try:
                value = eval(value)  # noqa: S307
            except NameError:
                self.log.warn(
                    "Error trying to evaluate %s at line %s", value, linenum
                )
            except SyntaxError:
                self.log.debug(
                    "Non-fatal SyntaxError at line %s while eval'ing '%s'",
                    linenum,
                    value,
                )

        # Actually use the value
        if not obj.hasProperty(name):
            obj._setProperty(name, value, type=proptype, setter=setter)
        else:
            obj._updateProperty(name, value)

    def addLink(self, rel, objid):
        """
        Build list of links to form after all objects have been created
        make sure that we don't add other side of a bidirectional relation

        @param rel: relationship object
        @type rel: relation object
        @param objid: objid
        @type objid: string
        """
        self.links.append((rel.getPrimaryId(), objid))

    def processLinks(self):
        """
        Walk through all the links that we saved and link them up
        """
        for relid, objid in self.links:
            try:
                self.log.debug(
                    "Linking relation %s to object %s", relid, objid
                )
                rel = getObjByPath(self.app, relid)
                obj = getObjByPath(self.app, objid)
                if not rel.hasobject(obj):
                    rel.addRelation(obj)
            except Exception:
                self.log.critical(
                    "Failed linking relation %s to object %s", relid, objid
                )

    def buildOptions(self):
        """
        Command-line options specific to this command
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            "-i",
            "--infile",
            dest="infile",
            help="Input file for import. Default is stdin",
        )
        self.parser.add_option(
            "--noindex",
            dest="noindex",
            action="store_true",
            default=False,
            help="Do not try to index the freshly loaded objects.",
        )
        self.parser.add_option(
            "--chunksize",
            dest="chunk_size",
            help="Number of objects to commit at a time.",
            type="int",
            default=100,
        )
        self.parser.add_option(
            "-n",
            "--noCommit",
            dest="noCommit",
            action="store_true",
            default=0,
            help="Do not store changes to the DMD (ie for debugging purposes)",
        )

    def loadObjectFromXML(self, xmlfile=""):
        """
        This method can be used to load data for the root of Zenoss (default
        behavior) or it can be used to operate on a specific point in the
        Zenoss hierarchy (ZODB).

        Upon loading the XML file to be processed, the content of the XML file
        is handled by the methods in this class when called by xml.sax.parse().

        Reads from a file if xmlfile is specified, otherwise reads
        from the command-line option --infile.  If no files are found from
        any of these places, read from standard input.

        @param xmlfile: Name of XML file to load, or file-like object
        @type xmlfile: string or file-like object
        """
        self.objstack = [self.app]
        self.links = []
        self.objectnumber = 0
        self.uncommittedObjects = 0
        self.charvalue = ""
        if xmlfile and isinstance(xmlfile, six.string_types):
            self.infile = open(xmlfile)
        elif hasattr(xmlfile, "read"):
            self.infile = xmlfile
        elif self.options.infile:
            self.infile = open(self.options.infile)
        else:
            self.infile = sys.stdin
        parser = make_parser()
        parser.setContentHandler(self)
        try:
            parser.parse(self.infile)
        except SAXParseException as ex:
            self.log.error(
                "XML parse error at line %d column %d: %s",
                ex.getLineNumber(),
                ex.getColumnNumber(),
                ex.getMessage(),
            )
        finally:
            self.infile.close()

    def loadDatabase(self):
        """
        The default behavior of loadObjectFromXML() will be to use the Zope
        app object, and thus operatate on the whole of Zenoss.
        """
        self.loadObjectFromXML()

    def commit(self):
        """
        Wrapper around the Zope database commit()
        """
        trans = transaction.get()
        trans.note(
            "Import from file %s using %s"
            % (self.options.infile, self.__class__.__name__)
        )
        trans.commit()
        self.uncommittedObjects = 0
        if hasattr(self, "connection"):
            # It's safe to call syncdb()
            self.syncdb()


class SpoofedOptions(object):
    """
    SpoofedOptions
    """

    def __init__(self):
        self.infile = ""
        self.noCommit = True
        self.noindex = True
        self.zodb_dataroot = "/zport/dmd"


class NoLoginImportRM(ImportRM):
    """
    An ImportRM that does not call the __init__ method on ZCmdBase
    """

    def __init__(self, app):
        """
        Initializer

        @param app: app
        @type app: string
        """
        from Products.ZenUtils.zenpackload import load_zenpacks
        from Zope2.App import zcml

        load_zenpacks()
        zcml.load_site()
        import logging

        self.log = logging.getLogger("zen.ImportRM")
        self.app = app
        ContentHandler.__init__(self)
        self.options = SpoofedOptions()
        self.dataroot = None
        self.getDataRoot()


def main():
    ImportRM().loadDatabase()
