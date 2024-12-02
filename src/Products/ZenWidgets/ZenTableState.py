##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ZenTableState

Track the state of a given table.
"""

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from DateTime.DateTime import DateTime
from persistent.dict import PersistentDict


class ZenTableState:

    defaultValue = ""  # So that we don't have to clear the session

    changesThatResetStart = [
        "batchSize",
        "filter",
        "sortedHeader",
        "sortedSence",
        "defaultValue",
        "onlyMonitored",
    ]

    requestAtts = [
        "batchSize",
        "filter",
        "filterFields",
        "sortedHeader",
        "sortedSence",
        "sortRule",
        "start",
        "URL",
        "defaultValue",
        "onlyMonitored",
        "generate",
    ]

    security = ClassSecurityInfo()
    # this session info isn't anything worth protecting
    security.setDefaultAccess("allow")

    def __init__(self, request, tableName, defaultBatchSize, **keys):
        self.URL = request.URL
        self.tableName = tableName
        self.sortedHeader = "primarySortKey"
        self.sortedSence = "asc"
        self.sortRule = "cmp"
        self.onlyMonitored = 0
        self.defaultBatchSize = defaultBatchSize
        self.batchSize = defaultBatchSize
        self.start = 0
        self.lastindex = 0
        self.filter = ""
        self.filterFields = []
        self.totalobjs = 0
        self.abbrStartLabel = 15
        self.defaultValue = ""
        self.abbrEndLabel = 5
        self.abbrPadding = 5
        self.abbrSeparator = ".."
        self.abbrThresh = (
            self.abbrStartLabel + self.abbrEndLabel + self.abbrPadding
        )
        self.tableClass = "tableheader"
        self.resetStart = False
        self.showAll = False
        self.setTableStateFromKeys(keys)
        self.generate = False

    def items(self):
        return self.__dict__.items()

    def keys(self):
        """
        Behave like a REQUEST, for report plugins that use REQUEST to pull
        objects (for example, the interface plugin)
        """
        return self.__dict__.keys()

    def values(self):
        """
        Behave like a REQUEST, for report plugins that use REQUEST to
        pull objects (for example, the interface plugin).
        """
        return self.__dict__.values()

    def setTableStateFromKeys(self, keys):
        self.__dict__.update(keys)
        for key in keys.keys():
            if key not in self.requestAtts:
                self.requestAtts.append(key)

    def updateFromRequest(self, request):
        """update table state based on request"""
        states = request.SESSION["zentablestates"]
        if not isinstance(states, PersistentDict):
            request.SESSION["zentablestates"] = PersistentDict(states)
        request.SESSION["zentablestates"]._p_changed = True
        if self.URL != request.URL:
            self.batchSize = self.defaultBatchSize
            self.start = 0
            self.filter = ""

        # 'tableName' will be empty on GET requests, therefore we check for
        # the 'showAll' option here.
        if (
            request.get("showAll", False)
            or "showAll=true" in request.get("QUERY_STRING")
            or request.get(
                "adapt", False or "adapt=false" in request.get("QUERY_STRING")
            )
        ):
            if not request.get("tableName", None):
                self.showAll = True
                self.start = 0
                self.batchSize = 0
                # The batch size needs to be set to the total object/result
                # count.  We don't have the objects here, so we will set the
                # batchSize where we do have the objects -- see
                # buildPageNavigation() below.

        if request.get("tableName", None) != self.tableName:
            return

        for attname in self.requestAtts:
            if request.has_key(attname):  # noqa W601
                self.setTableState(
                    attname,
                    int(request[attname])
                    if attname == "start"
                    else request[attname],
                    request=request,
                )
        if request.get("showAll", False) or "showAll=true" in request.get(
            "QUERY_STRING"
        ):
            self.showAll = True
            self.start = 0
            self.batchSize = 0
        if not request.has_key("onlyMonitored"):  # noqa W601
            self.setTableState("onlyMonitored", 0)
        if request.get("first", False):
            self.resetStart = True
        elif request.get("last", False):
            self.start = self.lastindex
        elif request.get("next", False):
            np = self.start + self.batchSize
            if np > self.lastindex:
                self.start = self.lastindex
            else:
                self.start = np
        elif request.get("prev", False):
            pp = self.start - self.batchSize
            if pp < 0:
                self.start = 0
            else:
                self.start = pp
        ourl = "/".join((request.URL, request.get("zenScreenName", "")))
        if self.resetStart or (self.URL != request.URL and self.URL != ourl):
            self.start = 0
            self.resetStart = False

    def getPageNavigation(self):
        return self.pagenav

    def buildPageNavigation(self, objects):
        self.pagenav = []
        if self.batchSize == 0:
            return self.pagenav
        lastindex = 0
        for index in range(0, self.totalobjs, self.batchSize):
            pg = {}
            pg["label"] = self._pageLabel(objects, index)
            pg["index"] = index
            self.pagenav.append(pg)
            lastindex = index
        self.lastindex = lastindex

    def _pageLabel(self, objects, index):
        """Make label for page navigation if field isn't sorted use page #."""
        pageLabel = ""
        # do not show the page label if there is only one page
        if self.totalobjs > self.batchSize:
            if self.sortedHeader:
                pageLabel = self._buildTextLabel(objects[index])
            elif self.batchSize:
                pageLabel = str(1 + index / self.batchSize)
            else:
                pageLabel = "1"
        return pageLabel

    def _buildTextLabel(self, item):
        startAbbr = ""
        endAbbr = ""
        attr = getattr(item, self.sortedHeader, self.defaultValue)
        if callable(attr):
            attr = attr()
        if isinstance(attr, DateTime) and not attr.millis():
            label = self.defaultValue
        else:
            label = attr
        if isinstance(item, dict):
            label = item.get(self.sortedHeader, "")
        # ensuring that we are always working with a string
        label = str(label)
        if len(label) > self.abbrThresh:
            startAbbr = label[: self.abbrStartLabel]
            if self.abbrEndLabel > 0:
                endAbbr = label[-self.abbrEndLabel :]
            label = "".join((startAbbr, self.abbrSeparator, endAbbr))
        return label

    def setTableState(
        self, attname, value, default=None, reset=False, request=None
    ):
        if attname == "batchSize":
            if value in ["", "0"]:
                value = 0
            else:
                # If given parameter is not numeric this will catch it
                try:
                    value = int(value)
                    if value <= 0:
                        raise ValueError("Page size cannot be negative")
                except ValueError:
                    # Restore whatever was the previous value
                    value = getattr(self, attname, None)
                    if request is not None:
                        # Set attribute in request to previous value so it
                        # gets stored properly.
                        request[attname] = value
        if not hasattr(self, attname) and default is not None:
            setattr(self, attname, default)
            if reset and attname not in self.changesThatResetStart:
                self.changesThatResetStart.append(attname)
            if attname not in self.requestAtts:
                self.requestAtts.append(attname)
        if value is not None and getattr(self, attname, None) != value:
            setattr(self, attname, value)
            if attname in self.changesThatResetStart:
                self.resetStart = True
        return getattr(self, attname)

    def addFilterField(self, fieldName):
        """make sure we only add non-dup filterfields"""
        if fieldName and fieldName not in self.filterFields:
            self.filterFields.append(fieldName)


InitializeClass(ZenTableState)
