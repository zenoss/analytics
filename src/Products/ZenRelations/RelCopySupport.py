##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""MultiCopySupport

MultiCopySupport over rides manage_pasteObjects in CopySupport to handle
cut/past for a MultiItem.  Semantics of cut/paste are to remove time from
current container and put it in new container but other container mappings
remain.

"""

from AccessControl import getSecurityManager
from App.Dialogs import MessageDialog
from OFS import Moniker
from OFS.CopySupport import (
    _cb_decode,
    CopyContainer,
    CopyError,
    eInvalid,
    eNoData,
    eNotFound,
)
from OFS.ObjectManager import checkValidId

from .Exceptions import ZenRelationsError


class RelCopyContainer(CopyContainer):
    def _checkId(self, new_id):
        """This method gets called from the new manage_renameObject which
        seems to be a bug in the Zope code. We add it until the problem is
        fixed.
        """
        checkValidId(self, new_id)

    def manage_linkObjects(self, ids=None, cb_copy_data=None, REQUEST=None):
        """link objects to relationship"""
        try:
            relName = self._getRelName(ids)
            oblist = self._getSourceObjects(cb_copy_data, REQUEST)
            for obj in oblist:
                self.manage_addRelation(relName, obj)
        except ZenRelationsError as e:
            if REQUEST:
                return MessageDialog(
                    title="Relationship Link Error",
                    message=str(e),
                    action="manage_main",
                )
            else:
                raise
        if REQUEST:
            return self.manage_main(self, REQUEST)

    def manage_unlinkObjects(self, ids=None, cb_copy_data=None, REQUEST=None):
        """unlink objects from relationship"""
        from Products.ZenUtils.Utils import unused

        unused(cb_copy_data)
        try:
            relName = self._getRelName(ids)
            self.manage_removeRelation(relName)
        except ZenRelationsError as e:
            if REQUEST:
                return MessageDialog(
                    title="Relationship Unlink Error",
                    message=str(e),
                    action="manage_main",
                )
            else:
                raise
        if REQUEST:
            return self.manage_main(self, REQUEST)

    def _verifyObjectPaste(self, object, validate_src=1):
        """
        check to see if this object is allowed to be pasted into this path
        """
        pathres = getattr(object, "relationshipManagerPathRestriction", None)
        if pathres and "/".join(self.getPhysicalPath()).find(pathres) == -1:
            raise CopyError(
                MessageDialog(
                    title="Not Supported",
                    message="The object <EM>%s</EM> can not be pasted into"
                    " the path <EM>%s</EM>"
                    % (object.id, "/".join(self.getPhysicalPath())),
                    action="manage_main",
                )
            )
        # We don't need this it checks for meta_type permissions
        # the check messes up zenhubs ability to rename devices
        # CopyContainer._verifyObjectPaste(self,object,validate_src)

    def _getRelName(self, ids):
        """
        Return our relationship name from the UI.
        If there is more than one id defined raise because only one
        target relationship can be defined.  If no ids are defined
        check to see that we are a ToManyRelationship and return self.id.
        """
        if not ids:
            if self.meta_type == "ToManyRelationship":
                return self.getId()
            else:
                raise ZenRelationsError("No relation name defined")
        if isinstance(ids, basestring):
            return ids
        if len(ids) > 1:
            raise ZenRelationsError("You can only link to one relationship!")
        return ids[0]

    def _verifyObjectLink(self):
        """
        When linking check that the user has "Copy or Move" permission
        on the relation.  Can't use _verifyObjectPaste because there
        is an empty all_meta_types on ToManyRelations which causes it
        to falsely fail.
        """
        if not getSecurityManager().checkPermission("Copy or Move", self):
            message = (
                'You do not possess the "Copy or Move" permission in '
                "the context of the container into which you are "
                "pasting, thus you are not able to perform "
                "this operation."
            )
            raise CopyError(
                MessageDialog(
                    title="Insufficient Privileges",
                    message=message,
                    action="manage_main",
                )
            )

    def _getSourceObjects(self, cb_copy_data, REQUEST):
        """get the source objects to link"""
        cp = None
        if cb_copy_data is not None:
            cp = cb_copy_data
        else:
            if REQUEST and "__cp" in REQUEST:
                cp = REQUEST["__cp"]
        if cp is None:
            raise CopyError(eNoData)

        try:
            cp = _cb_decode(cp)
        except Exception:
            raise CopyError(eInvalid)

        oblist = []
        app = self.getPhysicalRoot()

        for mdata in cp[1]:
            m = Moniker.loadMoniker(mdata)
            try:
                ob = m.bind(app)
            except Exception:
                raise CopyError(eNotFound)
            self._verifyObjectLink()
            oblist.append(ob)
        return oblist
