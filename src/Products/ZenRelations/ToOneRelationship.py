##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """ToOneRelationship

ToOneRelationship is a class used on a RelationshipManager
to give it toOne management Functions.
"""

import logging

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from App.special_dtml import DTMLFile
from zExceptions import NotFound

from Products.ZenUtils.Utils import getObjByPath

from .Exceptions import (
    ObjectNotFound,
    RelationshipExistsError,
    ZenSchemaError,
)
from .RelationshipBase import RelationshipBase

log = logging.getLogger("zen.Relations")


def manage_addToOneRelationship(context, id, REQUEST=None):
    """ToOneRelationship Factory"""
    r = ToOneRelationship(id)
    context._setObject(id, r)
    if REQUEST:
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )


addToOneRelationship = DTMLFile("dtml/addToOneRelationship", globals())


# FIXME - please make me go away, I'm so ugly!
def getPrimaryLink(obj, target=None):
    """
    Gets the object's PrimaryLink
    """
    link = ""
    if obj:
        if not obj.checkRemotePerm("View", obj):
            link = obj.id
        else:
            attributes = ""
            if target is not None:
                attributes = "target='%s' " % (target,)
            link = "<a %shref='%s'>%s</a>" % (
                attributes,
                obj.getPrimaryUrlPath(),
                obj.id,
            )
    return link


class ToOneRelationship(RelationshipBase):
    """ToOneRelationship represents a to one Relationship
    on a RelationshipManager"""

    meta_type = "ToOneRelationship"

    security = ClassSecurityInfo()

    def __init__(self, id):
        self.id = id
        self.obj = None

    def __call__(self):
        """return the related object when a ToOne relation is called"""
        # Disabling relationship checking code.
        # http://dev.zenoss.org/trac/ticket/5391
        # self.checkRelation(True)
        return self.obj

    def hasobject(self, obj):
        """does this relation point to the object passed"""
        return self.obj == obj

    def _add(self, obj):
        """add a to one side of a relationship
        if a relationship already exists clear it"""
        if obj == self.obj:
            raise RelationshipExistsError
        self._remoteRemove()
        self.obj = aq_base(obj)
        self.__primary_parent__._p_changed = True

    def _remove(self, obj=None, suppress_events=False):
        """remove the to one side of a relationship"""
        if obj is None or obj == self.obj:
            self.obj = None
            self.__primary_parent__._p_changed = True
        else:
            raise ObjectNotFound("object %s was not found on %s" % (obj, self))

    def _remoteRemove(self, obj=None):
        """clear the remote side of this relationship"""
        if self.obj:
            if obj is not None and obj != self.obj:
                raise ObjectNotFound(
                    "object %s was not found on %s it has object %s"
                    % (
                        obj.getPrimaryId(),
                        self.getPrimaryId(),
                        self.obj.getPrimaryId(),
                    )
                )
            remoteRel = getattr(aq_base(self.obj), self.remoteName())
            try:
                remoteRel._remove(self.__primary_parent__)
            except ObjectNotFound:
                log.debug(
                    "remote relation already removed  "
                    "obj=%s remote-relation=%s",
                    self.__primary_parent__.getPrimaryId(),
                    remoteRel.getPrimaryId(),
                )

    security.declareProtected("View", "getRelatedId")

    def getRelatedId(self):
        """return the id of the our related object"""
        if self.obj:
            return self.obj.id
        else:
            return None

    def _getCopy(self, container):
        """
        Create ToOne copy. If this is the one side of one to many
        we set our side of the relation to point towards the related
        object (maintain the relationship across the copy).
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'zNoRelationshipCopy', [])
        if self.id in norelcopy:
            return rel
        if self.remoteTypeName() == "ToMany" and self.obj:
            rel.addRelation(self.obj)
        return rel

    def manage_afterAdd(self, item, container):
        """Don't do anything here because we have on containment"""
        pass

    def manage_afterClone(self, item):
        """Don't do anything here because we have on containment"""
        pass

    def manage_workspace(self, REQUEST):
        """ZMI function to return the workspace of the related object"""
        if self.obj:
            objurl = self.obj.getPrimaryUrlPath()
            REQUEST["RESPONSE"].redirect(objurl + "/manage_workspace")
        else:
            return MessageDialog(
                title="No Relationship Error",
                message="This relationship does not currently point"
                " to an object",
                action="manage_main",
            )

    def manage_main(self, REQUEST=None):
        """ZMI function to redirect to parent relationship manager"""
        REQUEST["RESPONSE"].redirect(
            self.getPrimaryParent().getPrimaryUrlPath() + "/manage_workspace"
        )

    security.declareProtected("View", "getPrimaryLink")

    def getPrimaryLink(self, target=None):
        """get the link tag of a related object"""
        return getPrimaryLink(self.obj, target)

    def getPrimaryHref(self):
        """Return the primary URL for our related object."""
        return self.obj.getPrimaryUrlPath()

    def exportXml(self, ofile, ignorerels=()):
        """return an xml representation of a ToOneRelationship
        <toone id='cricket'>
            /Monitors/Cricket/crk0.srv.hcvlny.cv.net
        </toone>"""
        from RelSchema import ToManyCont

        if not self.obj or self.remoteType() == ToManyCont:
            return
        try:
            ofile.write(
                "<toone id='%s' objid='%s'/>\n"
                % (self.id, self.obj.getPrimaryId())
            )
        except Exception:
            log.exception(
                "skipping %s  object-type=%s object-id=%s",
                self.id,
                self.obj.__class__.__module__,
                getattr(self.obj, "id", "<no-id-attribute>"),
            )

    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok."""
        if not self.obj:
            return
        log.debug("checking relation: %s", self.id)

        try:
            ppath = self.obj.getPrimaryPath()
            getObjByPath(self, ppath)
        except (KeyError, NotFound):
            log.error(
                "object %s in relation %s has been deleted "
                "from its primary path",
                self.obj.getPrimaryId(),
                self.getPrimaryId(),
            )
            if repair:
                log.warn(
                    "removing object %s from relation %s",
                    self.obj.getPrimaryId(),
                    self.getPrimaryId(),
                )
                self.obj = None

        if not self.obj:
            return

        parobj = self.getPrimaryParent()
        try:
            rname = self.remoteName()
        except ZenSchemaError:
            path = parobj.getPrimaryUrlPath()
            log.exception(
                "Object %s (parent %s) has a bad schema", self.obj, path
            )
            log.warn("Might be able to fix by re-installing ZenPack")
            return

        rrel = getattr(self.obj, rname)
        if not rrel.hasobject(parobj):
            log.error(
                "remote relation %s doesn't point back to %s",
                rrel.getPrimaryId(),
                self.getPrimaryId(),
            )
            if repair:
                log.warn(
                    "reconnecting relation %s to relation %s",
                    rrel.getPrimaryId(),
                    self.getPrimaryId(),
                )
                rrel._add(parobj)


InitializeClass(ToOneRelationship)
