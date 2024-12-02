##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import marshal
import time

import App
import App.Management
import AccessControl
import AccessControl.Owned
import App.Common

from AccessControl import getSecurityManager, Unauthorized
from AccessControl.ZopeSecurityPolicy import getRoles
from Acquisition import aq_base, aq_parent, aq_inner, Acquired
from App.special_dtml import DTMLFile
from ComputedAttribute import ComputedAttribute
from ExtensionClass import Base
from OFS.CopySupport import CopySource
from OFS.Traversable import Traversable
from zExceptions import Redirect
from zExceptions.ExceptionFormatter import format_exception

from Products.ZenUtils.Utils import unused

logger = logging.getLogger()


class ZItem(
    Base,
    CopySource,
    App.Management.Tabs,
    Traversable,
    AccessControl.Owned.Owned,
):

    """A common base class for simple, non-container objects."""

    isPrincipiaFolderish = 0
    isTopLevelPrincipiaApplicationObject = 0

    # Direct use of the 'id' attribute is deprecated - use getId()
    id = ""

    getId__roles__ = None

    def getId(self):
        """Return the id of the object as a string.

        This method should be used in preference to accessing an id attribute
        of an object directly. The getId method is public.
        """
        name = getattr(self, "id", None)
        if callable(name):
            return name()
        if name is not None:
            return name
        if hasattr(self, "__name__"):
            return self.__name__
        raise AttributeError("This object has no id")

    # Alias id to __name__, which will make tracebacks a good bit nicer:
    __name__ = ComputedAttribute(lambda self: self.getId())

    # Name, relative to SOFTWARE_URL of icon used to display item
    # in folder listings.
    icon = ""

    # Meta type used for selecting all objects of a given type.
    meta_type = "simple item"

    # Default title.
    title = ""

    # Default propertysheet info:
    __propsets__ = ()

    manage_options = AccessControl.Owned.Owned.manage_options

    # Attributes that must be acquired
    REQUEST = Acquired

    # Allow (reluctantly) access to unprotected attributes
    __allow_access_to_unprotected_subobjects__ = 1

    def title_or_id(self):
        """Return the title if it is not blank and the id otherwise."""
        title = self.title
        if callable(title):
            title = title()
        if title:
            return title
        return self.getId()

    def titleOrId(self):
        """Return the title if it is not blank and the id otherwise"""
        return self.title_or_id()

    def title_and_id(self):
        """Return the title if it is not blank and the id otherwise.

        If the title is not blank, then the id is included in parens.
        """
        title = self.title
        if callable(title):
            title = title()
        id = self.getId()
        return title and ("%s (%s)" % (title, id)) or id

    def this(self):
        # Handy way to talk to ourselves in document templates.
        return self

    def tpURL(self):
        # My URL as used by tree tag
        return self.getId()

    def tpValues(self):
        # My sub-objects as used by the tree tag
        return ()

    _manage_editedDialog = DTMLFile("dtml/editedDialog", globals())

    def manage_editedDialog(self, REQUEST, **args):
        return apply(self._manage_editedDialog, (self, REQUEST), args)

    def manage(self, URL1):
        """ """
        raise Redirect("%s/manage_main" % URL1)

    # This keeps simple items from acquiring their parents
    # objectValues, etc., when used in simple tree tags.
    def objectValues(self, spec=None):
        unused(spec)
        return ()

    objectIds = objectItems = objectValues

    # FTP support methods

    def manage_FTPstat(self, REQUEST):
        """Psuedo stat, used by FTP for directory listings."""
        from AccessControl.User import nobody

        mode = 0o100000

        if hasattr(aq_base(self), "manage_FTPget"):
            try:
                if getSecurityManager().validate(
                    None, self, "manage_FTPget", self.manage_FTPget
                ):
                    mode = mode | 0o440
            except Unauthorized:
                pass

            if nobody.allowed(
                self.manage_FTPget,
                getRoles(self, "manage_FTPget", self.manage_FTPget, ()),
            ):
                mode = mode | 0o004

        # check write permissions
        if hasattr(aq_base(self), "PUT"):
            try:
                if getSecurityManager().validate(None, self, "PUT", self.PUT):
                    mode = mode | 0o220
            except Unauthorized:
                pass

            if nobody.allowed(
                self.PUT,
                getRoles(self, "PUT", self.PUT, ()),
            ):
                mode = mode | 0o002

        # get size
        if hasattr(aq_base(self), "get_size"):
            size = self.get_size()
        elif hasattr(aq_base(self), "manage_FTPget"):
            size = len(self.manage_FTPget())
        else:
            size = 0
        # get modification time
        if hasattr(aq_base(self), "bobobase_modification_time"):
            mtime = self.bobobase_modification_time().timeTime()
        else:
            mtime = time.time()
        # get owner and group
        owner = group = "Zope"
        if hasattr(aq_base(self), "get_local_roles"):
            for user, roles in self.get_local_roles():
                if "Owner" in roles:
                    owner = user
                    break
        return marshal.dumps(
            (mode, 0, 0, 1, owner, group, size, mtime, mtime, mtime)
        )

    def manage_FTPlist(self, REQUEST):
        """Directory listing for FTP.

        In the case of non-Foldoid objects, the listing should contain one
        object, the object itself.
        """
        # check to see if we are being acquiring or not
        ob = self
        while 1:
            if App.Common.is_acquired(ob):
                raise ValueError("FTP List not supported on acquired objects")
            if not hasattr(ob, "aq_parent"):
                break
            ob = ob.aq_parent

        stat = marshal.loads(self.manage_FTPstat(REQUEST))
        id = self.getId()
        return marshal.dumps((id, stat))

    def __len__(self):
        return 1

    def __repr__(self):
        """
        Show the physical path of the object and its context if available.
        """
        try:
            path = "/".join(self.getPhysicalPath())
        except Exception:
            return Base.__repr__(self)
        context_path = None
        context = aq_parent(self)
        container = aq_parent(aq_inner(self))
        if aq_base(context) is not aq_base(container):
            try:
                context_path = "/".join(context.getPhysicalPath())
            except Exception:
                context_path = None
        res = "<%s" % self.__class__.__name__
        res += " at %s" % path
        if context_path:
            res += " used for %s" % context_path
        res += ">"
        return res


def pretty_tb(t, v, tb, as_html=1):
    tb = format_exception(t, v, tb, as_html=as_html)
    tb = "\n".join(tb)
    return tb
