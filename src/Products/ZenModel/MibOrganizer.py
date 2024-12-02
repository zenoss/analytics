##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

import six

from AccessControl import ClassSecurityInfo, Permissions
from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile

from Products.Jobber.jobs import SubprocessJob
from Products.ZenRelations.RelSchema import ToOne, ToManyCont
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
from Products.ZenWidgets import messaging
from Products.ZenUtils.Utils import atomicWrite, binPath, zenPath

from .MibModule import MibModule
from .Organizer import Organizer
from .ZenossSecurity import ZEN_MANAGE_DMD, ZEN_ADD
from .ZenPackable import ZenPackable

log = logging.getLogger("zen.Mibs")
_pathToMIB = "var/ext/uploadedMIBs"


def manage_addMibOrganizer(context, id, REQUEST=None):
    """make a device class"""
    sc = MibOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )


addMibOrganizer = DTMLFile("dtml/addMibOrganizer", globals())


def _oid2name(mibSearch, oid, exactMatch=True, strip=False):
    """Return a name for an oid. This function is extracted out of the
    MibOrganizer class and takes mibSearch as a parameter to make it easier to
    unit test.
    """
    oid = oid.strip(".")

    if exactMatch:
        brains = mibSearch(oid=oid)
        if len(brains) > 0:
            return brains[0].id
        else:
            return ""

    oidlist = oid.split(".")
    for i in range(len(oidlist), 0, -1):
        brains = mibSearch(oid=".".join(oidlist[:i]))
        if len(brains) < 1:
            continue
        if len(oidlist[i:]) > 0 and not strip:
            return "%s.%s" % (brains[0].id, ".".join(oidlist[i:]))
        else:
            return brains[0].id
    return ""


class MibOrganizer(Organizer, ZenPackable):
    meta_type = "MibOrganizer"
    dmdRootName = "Mibs"
    default_catalog = "mibSearch"

    security = ClassSecurityInfo()

    _relations = (
        Organizer._relations
        + ZenPackable._relations
        + (
            (
                "mibs",
                ToManyCont(
                    ToOne, "Products.ZenModel.MibModule", "miborganizer"
                ),
            ),
        )
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            "immediate_view": "mibOrganizerOverview",
            "actions": (
                {
                    "id": "overview",
                    "name": "Overview",
                    "action": "mibOrganizerOverview",
                    "permissions": (Permissions.view,),
                },
            ),
        },
    )

    def __init__(
        self, id=None, description=None, text=None, content_type="text/html"
    ):
        if not id:
            id = self.dmdRootName
        super(MibOrganizer, self).__init__(id, description)
        if self.id == self.dmdRootName:
            self.createCatalog()

    def getMibClass(self):
        return MibOrganizer

    def countMibs(self):
        """Return a count of all our contained children."""
        count = len(self.mibs())
        for child in self.children():
            count += child.countMibs()
        return count

    def oid2name(self, oid, exactMatch=True, strip=False):
        """
        Return a name for an oid.
        """
        return _oid2name(
            self.getDmdRoot("Mibs").mibSearch, oid, exactMatch, strip
        )

    def name2oid(self, name):
        """
        Return an oid based on a name in the form MIB::name.
        """
        brains = self.getDmdRoot("Mibs").mibSearch({"id": name})
        if len(brains) > 0:
            return brains[0].oid
        return ""

    def countClasses(self):
        """Count all mibs with in a MibOrganizer."""
        count = self.mibs.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count

    def createMibModule(self, name, path="/"):
        """Create a MibModule"""
        mibs = self.getDmdRoot(self.dmdRootName)
        mod = None
        if not mod:
            modorg = mibs.createOrganizer(path)
            mod = MibModule(name)
            modorg.mibs._setObject(mod.id, mod)
            mod = modorg.mibs._getOb(mod.id)
        return mod

    def manage_addMibModule(self, id, REQUEST=None):
        """Create a new service class in this Organizer."""
        mm = MibModule(id)
        self.mibs._setObject(id, mm)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Mib Module Created", "Mib module %s was created." % id
            )
            return self.callZenScreen(REQUEST)
        else:
            return self.mibs._getOb(id)

    def removeMibModules(self, ids=None, REQUEST=None):
        """Remove MibModules from an EventClass."""
        if not ids:
            return self()
        if isinstance(ids, six.string_types):
            ids = (ids,)
        for id in ids:
            self.mibs._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Mib Module Deleted",
                "Mib modules deleted: %s" % ", ".join(ids),
            )
            return self()

    def moveMibModules(self, moveTarget, ids=None, REQUEST=None):
        """Move MibModules from this organizer to moveTarget."""
        if isinstance(ids, six.string_types):
            ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.mibs._getOb(id)
            rec._operation = 1  # moving object state
            self.mibs._delObject(id)
            target.mibs._setObject(id, rec)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Mib Module Moved", "Mib modules moved to %s." % moveTarget
            )
            REQUEST["RESPONSE"].redirect(target.getPrimaryUrlPath())

    security.declareProtected(ZEN_MANAGE_DMD, "reIndex")

    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        for org in [self] + self.getSubOrganizers():
            for mib in org.mibs():
                for thing in mib.nodes() + mib.notifications():
                    thing.index_object()

    security.declareProtected(ZEN_ADD, "createCatalog")

    def createCatalog(self):
        """Create a catalog for mibs searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX update to use ManagableIndex
        manage_addZCatalog(self, self.default_catalog, self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex("oid", makeCaseInsensitiveKeywordIndex("oid"))
        cat.addIndex("id", makeCaseInsensitiveKeywordIndex("id"))
        cat.addIndex("summary", makeCaseInsensitiveKeywordIndex("summary"))
        zcat.addColumn("getPrimaryId")
        zcat.addColumn("id")
        zcat.addColumn("oid")

    def handleUploadedFile(self, REQUEST):
        """
        Assumes the file to be a mib so we need to create a mib module with
        its contents
        File will be available with REQUEST.upload
        """
        filename = REQUEST.upload.filename
        mibs = REQUEST.upload.read()
        savedMIBPath = zenPath(_pathToMIB, filename)
        atomicWrite(savedMIBPath, mibs, raiseException=True, createDir=True)

        # create the job
        mypath = self.absolute_url_path().replace("/zport/dmd/Mibs", "")
        if not mypath:
            mypath = "/"
        commandArgs = [
            binPath("zenmib"),
            "run",
            savedMIBPath,
            "--path=%s" % mypath,
            "--mibdepsdir=%s" % zenPath(_pathToMIB),
        ]
        return self.dmd.JobManager.addJob(
            SubprocessJob,
            description="Load MIB at %s" % mypath,
            kwargs={"cmd": commandArgs},
        )


InitializeClass(MibOrganizer)
