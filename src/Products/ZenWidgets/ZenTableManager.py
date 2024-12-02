##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ZenTableManager

ZenTableManager is a Zope Product that helps manage and display large sets of
tabular data.  It allows for column sorting, break down of the set into pages,
and filtering of elements in the table.  It also allows users to store their
own default page size (but publishes a hook to get this values from a
different location).
"""

import logging
import math
import re
import urllib

import ZTUtils

from Acquisition import aq_base
from AccessControl.class_init import InitializeClass
from DocumentTemplate.sequence.SortEx import sort
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from persistent.dict import PersistentDict

from Products.ZenUtils.Utils import getTranslation

from .ZenTableState import ZenTableState

log = logging.getLogger("zen.ZenTableManager")


class TableStateNotFound(Exception):
    pass


def convert(x):
    return 0.0 if isinstance(x, float) and math.isnan(x) else x


def zencmp(o1, o2):
    return cmp(convert(o1), convert(o2))


def manage_addZenTableManager(context, id="", REQUEST=None):
    """Make a CVDeviceLoader."""
    if not id:
        id = "ZenTableManager"
    ztm = ZenTableManager(id)
    context._setObject(id, ztm)
    ztm = context._getOb(id)
    ztm.initTableManagerSkins()

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url_path() + "/manage_main")


class ZenTableManager(SimpleItem, PropertyManager):
    """ZenTableManager manages display of tabular data."""

    portal_type = meta_type = "ZenTableManager"

    _properties = (
        {"id": "defaultBatchSize", "type": "int", "mode": "w"},
        {"id": "abbrStartLabel", "type": "int", "mode": "w"},
        {"id": "abbrEndLabel", "type": "int", "mode": "w"},
        {"id": "abbrPadding", "type": "int", "mode": "w"},
        {"id": "abbrSeparator", "type": "string", "mode": "w"},
    )

    manage_options = PropertyManager.manage_options + SimpleItem.manage_options

    def __init__(self, id):
        self.id = id
        self.defaultBatchSize = 40
        self.abbrStartLabel = 15
        self.abbrEndLabel = 5
        self.abbrPadding = 5
        self.abbrSeparator = ".."
        self.abbrThresh = (
            self.abbrStartLabel + self.abbrEndLabel + self.abbrPadding
        )

    def getDefaultBatchSize(self):
        dbs = self.defaultBatchSize
        zu = getattr(self, "ZenUsers", None)
        if zu and zu.getUserSettings():
            dbs = zu.getUserSettings().defaultPageSize
        return dbs

    def setupTableState(self, tableName, **keys):
        """Initialize or setup the session variable to track table state."""
        tableState = self.getTableState(tableName, **keys)
        request = self.REQUEST
        tableState.updateFromRequest(request)
        return tableState

    def getTableState(self, tableName, attrname=None, default=None, **keys):
        """Return an existing table state or a single value from the state."""
        from Products.ZenUtils.Utils import unused

        unused(default)
        request = self.REQUEST
        tableStates = self.getTableStates()
        tableState = tableStates.get(tableName, None)
        if not tableState:
            dbs = self.getDefaultBatchSize()
            tableStates[tableName] = ZenTableState(
                request, tableName, dbs, **keys
            )
            tableState = tableStates[tableName]
        if attrname is None:
            return tableStates[tableName]
        return getattr(tableState, attrname, None)

    def getReqTableState(self, tableName, attrname):
        """
        Return attrname from request if present if not return from tableState.
        """
        request = self.REQUEST
        if request.has_key(attrname):  # noqa W601
            return request[attrname]
        return self.getTableState(tableName, attrname)

    def setTableState(self, tableName, attrname, value):
        """Set the value of a table state attribute and return it."""
        tableState = self.getTableState(tableName)
        return tableState.setTableState(attrname, value)

    def setReqTableState(self, tableName, attrname, default=None, reset=False):
        """Set the a value in the table state from the request."""
        tableState = self.getTableState(tableName)
        value = self.REQUEST.get(attrname, None)
        tableState = self.getTableState(tableName)
        return tableState.setTableState(
            attrname, value, default=default, reset=reset
        )

    def deleteTableState(self, tableName):
        """Delete an existing table state."""
        tableStates = self.getTableStates()

        if tableName in tableStates:
            del tableStates[tableName]

    def getBatch(self, tableName, objects, **keys):
        """Filter, sort and batch objects and pass return set."""
        if log.isEnabledFor(logging.DEBUG):
            import os

            fmt = "getBatch pid=%s, tableName=%s, %s objects"
            pid = os.getpid()
            log.debug(fmt, pid, tableName, len(objects))
        if not objects:
            objects = []
        tableState = self.setupTableState(tableName, **keys)
        if tableState.onlyMonitored and objects:
            objects = [
                o for o in objects if getattr(o, "isMonitored", o.monitored)()
            ]
        if tableState.filter and objects:
            objects = self.filterObjects(
                objects, tableState.filter, tableState.filterFields
            )
        # objects is frequently a generator.  Need a list in order to sort
        if not isinstance(objects, list):
            objects = list(objects)
        if tableState.sortedHeader:
            objects = self.sortObjects(objects, tableState)
        tableState.totalobjs = len(objects)
        tableState.buildPageNavigation(objects)
        if not hasattr(self.REQUEST, "doExport"):
            objects = ZTUtils.Batch(
                objects,
                tableState.batchSize or len(objects),
                start=tableState.start,
                orphan=0,
            )
        return objects

    def getBatchForm(self, objects, request):
        """Create batch based on objects no sorting for filter applied."""
        batchSize = request.get("batchSize", self.defaultBatchSize)
        if batchSize in ["", "0"]:
            batchSize = 0
        else:
            batchSize = int(batchSize)
        start = int(request.get("start", 0))
        resetStart = int(request.get("resetStart", 0))
        lastindex = request.get("lastindex", 0)
        navbutton = request.get("navbutton", None)
        if navbutton == "first" or resetStart:
            start = 0
        elif navbutton == "last":
            start = lastindex
        elif navbutton == "next":
            start = start + batchSize
            if start > lastindex:
                start = lastindex
        elif navbutton == "prev":
            start = start - batchSize
        elif request.has_key("nextstart"):  # noqa W601
            start = request.nextstart
        if 0 < start > len(objects):
            start = 0
        request.start = start
        objects = ZTUtils.Batch(
            objects, batchSize or len(objects), start=request.start, orphan=0
        )
        return objects

    def filterObjects(self, objects, regex, filterFields):
        """Filter objects base on a regex in regex and list of fields
        in filterFields."""
        if self.REQUEST.SESSION.has_key("message"):  # noqa W601
            self.REQUEST.SESSION.delete("message")
        if not regex:
            return objects
        try:
            search = re.compile(regex, re.I).search
        except re.error:
            self.REQUEST.SESSION["message"] = "Invalid regular expression."
            return objects
        filteredObjects = []
        for obj in objects:
            target = []
            for field in filterFields:
                if isinstance(obj, dict):
                    value = obj.get(field, None)
                else:
                    value = getattr(obj, field, None)
                if callable(value):
                    value = value()
                if not isinstance(value, basestring):
                    value = str(value)
                target.append(value)
            targetstring = " ".join(target)
            if search(targetstring):
                filteredObjects.append(obj)
        return filteredObjects

    def evaluateTales(self, expression, dev):
        log.warning("evaluating %s", dev.__dict__)
        variables_and_funcs = {"device": dev, "dev": dev}
        expression = expression.replace("python:", "attr=")
        try:
            exec (expression, variables_and_funcs)
            attr = variables_and_funcs["attr"]
            log.warning("attr is %s", attr)
        except Exception as ex:
            attr = str(ex)
        return attr

    def sortObjects(self, objects, request):
        """Sort objects."""

        def dictAwareSort(objects, field, rule, sence):
            if not objects:
                return objects

            class Wrapper:
                def __init__(self, field, cargo):
                    if callable(field):
                        field = field()
                    # make sorting case-insensitive
                    if isinstance(field, basestring):
                        field = field.lower()
                    self.field = field
                    self.cargo = cargo

            if field.startswith("python:"):
                objects = [
                    Wrapper(self.evaluateTales(field, o), o) for o in objects
                ]
            else:
                if isinstance(objects[0], dict):
                    objects = [Wrapper(o.get(field, ""), o) for o in objects]
                else:
                    objects = [
                        Wrapper(getattr(o, field, ""), o) for o in objects
                    ]
            objects = sort(
                objects, (("field", rule, sence),), {"zencmp": zencmp}
            )
            return [w.cargo for w in objects]

        if getattr(aq_base(request), "sortedHeader", False) and getattr(
            aq_base(request), "sortedSence", False
        ):
            sortedHeader = request.sortedHeader
            sortedSence = request.sortedSence
            sortRule = getattr(aq_base(request), "sortRule", "cmp")
            objects = dictAwareSort(
                objects, sortedHeader, sortRule, sortedSence
            )

        return objects

    def getTableHeader(
        self,
        tableName,
        fieldName,
        fieldTitle,
        sortRule="cmp",
        style="tableheader",
        attributes="",
        i18n_domain="zenoss",
    ):
        """Generate a <th></th> tag that allows column sorting."""
        href = self.getTableHeaderHref(tableName, fieldName, sortRule)
        style = self.getTableHeaderStyle(tableName, fieldName, style)
        tag = """<th class="%s" %s>""" % (style, attributes)
        tag += """<a class="%s" href="%s""" % (style, href)

        # Owwwwwwwwwww
        from Products.Zuul.utils import ZuulMessageFactory as _t

        msg = getTranslation(_t(fieldTitle), self.REQUEST, domain=i18n_domain)
        tag += msg + "</a></th>\n"

        return tag

    def getTableHeaderHref(
        self, tableName, fieldName, sortRule="cmp", params=""
    ):
        """Build the href attribute for the table headers."""
        tableState = self.getTableState(tableName)
        sortedHeader = tableState.sortedHeader
        sortedSence = tableState.sortedSence
        if sortedHeader == fieldName:
            if sortedSence == "asc":
                sortedSence = "desc"
            elif sortedSence == "desc":
                sortedSence = "asc"
        else:
            sortedSence = "asc"
        href = "%s?tableName=%s&sortedHeader=%s&" % (
            self.REQUEST.URL,
            tableName,
            urllib.quote_plus(fieldName),
        )
        href += 'sortedSence=%s&sortRule=%s%s">' % (
            sortedSence,
            sortRule,
            params,
        )
        tableState.addFilterField(fieldName)
        return href

    def getTableHeaderStyle(self, tableName, fieldName, style):
        """apends "selected" onto the CSS style if this field is selected"""
        if self.getTableState(tableName, "sortedHeader") == fieldName:
            style = style + "selected"
        return style

    def getTableStates(self):
        session = self.REQUEST.SESSION
        try:
            return session["zentablestates"]
        except KeyError:
            init = PersistentDict()
            session["zentablestates"] = init
            return init

    def tableStatesHasTable(self, tableName):
        return tableName in self.getTableStates()

    def getNavData(self, objects, batchSize, sortedHeader):
        pagenav = []
        if batchSize in ["", "0"]:
            batchSize = 0
        else:
            batchSize = int(batchSize)
        for index in range(0, len(objects), batchSize or len(objects)):
            if sortedHeader:
                label = self._buildTextLabel(objects[index], sortedHeader)
            elif batchSize:
                label = str(1 + index / batchSize)
            else:
                label = "1"
            pagenav.append({"label": label, "index": index})
        return pagenav

    def _buildTextLabel(self, item, sortedHeader):
        endAbbr = ""
        attr = getattr(item, sortedHeader, "")
        if callable(attr):
            attr = attr()
        label = str(attr)
        if len(label) > self.abbrThresh:
            startAbbr = label[: self.abbrStartLabel]
            if self.abbrEndLabel > 0:
                endAbbr = label[-self.abbrEndLabel :]
            label = "".join((startAbbr, self.abbrSeparator, endAbbr))
        return label

    def initTableManagerSkins(self):
        """setup the skins that come with ZenTableManager"""
        layers = ("zentablemanager", "zenui")
        try:
            import string
            from Products.CMFCore.utils import getToolByName
            from Products.CMFCore.DirectoryView import addDirectoryViews

            skinstool = getToolByName(self, "portal_skins")
            for layer in layers:
                if layer not in skinstool.objectIds():
                    addDirectoryViews(skinstool, "skins", globals())
            skins = skinstool.getSkinSelections()
            for skin in skins:
                path = skinstool.getSkinPath(skin)
                path = map(string.strip, string.split(path, ","))
                for layer in layers:
                    if layer not in path:
                        try:
                            path.insert(path.index("custom") + 1, layer)
                        except ValueError:
                            path.append(layer)
                path = ",".join(path)
                skinstool.addSkinSelection(skin, path)
        except ImportError as e:
            if "Products.CMFCore.utils" in e.args:
                pass
            else:
                raise
        except AttributeError as e:
            if "portal_skin" in e.args:
                pass
            else:
                raise


InitializeClass(ZenTableManager)
