##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
This module patches CMFCore DirectoryViews to allow unauthenticated users
access to filesystem-based resources. This is necessary for ZenDeviceACL to
function.
"""

#######################################################
# DirectoryView imports
#######################################################
import logging
from os import path
from OFS.ObjectManager import bad_id

from Products.CMFCore.FSMetadata import FSMetadata
from Products.CMFCore.FSObject import BadFile

logger = logging.getLogger('CMFCore.DirectoryView')

#######################################################
# Imports from DirectoryView itself
#######################################################
from Products.CMFCore.DirectoryView import _filtered_listdir
from Products.CMFCore.DirectoryView import DirectoryView

#######################################################
# The only import we need
#######################################################
from Products.ZenUtils.Utils import monkeypatch

@monkeypatch(FSMetadata)
def read(self):
    """ Find the files to read, either the old security and
    properties type or the new metadata type """
    filename = self._filename + '.metadata'
    if path.exists(filename):
        # found the new type, lets use that
        self._readMetadata()
    else:
###########################################################################
# This is a monkeypatch. CMFCore 2.0 returns {} where 1.x returned
# None; we rely on None. {} is (maybe) ambiguous.
###########################################################################
        self._properties = None
        self._security = None
###########################################################################
# End monkeypatch
###########################################################################


@monkeypatch('Products.CMFCore.DirectoryView.DirectoryInformation')
def prepareContents(self, registry, register_subdirs=0):
    # Creates objects for each file.
    data = {}
    objects = []
    types = self._readTypesFile()
    for entry in _filtered_listdir(self._filepath, ignore=self.ignore):
        if not self._isAllowableFilename(entry):
            continue
        entry_filepath = path.join(self._filepath, entry)
        if path.isdir(entry_filepath):
            # Add a subdirectory only if it was previously registered,
            # unless register_subdirs is set.
            entry_reg_key = '/'.join((self._reg_key, entry))
            info = registry.getDirectoryInfo(entry_reg_key)
            if info is None and register_subdirs:
                # Register unknown subdirs
                registry.registerDirectoryByKey(entry_filepath,
                                                entry_reg_key)
                info = registry.getDirectoryInfo(entry_reg_key)
            if info is not None:
                # Folders on the file system have no extension or
                # meta_type, as a crutch to enable customizing what gets
                # created to represent a filesystem folder in a
                # DirectoryView we use a fake type "FOLDER". That way
                # other implementations can register for that type and
                # circumvent the hardcoded assumption that all filesystem
                # directories will turn into DirectoryViews.
                mt = types.get(entry) or 'FOLDER'
                t = registry.getTypeByMetaType(mt)
                if t is None:
                    t = DirectoryView
                metadata = FSMetadata(entry_filepath)
                metadata.read()
                ob = t( entry
                      , entry_reg_key
                      , properties=metadata.getProperties()
                      )
                ob_id = ob.getId()
                data[ob_id] = ob
                objects.append({'id': ob_id, 'meta_type': ob.meta_type})
        else:
            pos = entry.rfind('.')
            if pos >= 0:
                name = entry[:pos]
                ext = path.normcase(entry[pos + 1:])
            else:
                name = entry
                ext = ''
            if not name or name == 'REQUEST':
                # Not an allowable id.
                continue
            mo = bad_id(name)
            if mo is not None and mo != -1:  # Both re and regex formats
                # Not an allowable id.
                continue
            t = None
            mt = types.get(entry, None)
            if mt is None:
                mt = types.get(name, None)
            if mt is not None:
                t = registry.getTypeByMetaType(mt)
            if t is None:
                t = registry.getTypeByExtension(ext)

            if t is not None:
                metadata = FSMetadata(entry_filepath)
                metadata.read()
                try:
                    ob = t(name, entry_filepath, fullname=entry,
                           properties=metadata.getProperties())
                except Exception:
                    import sys
                    import traceback
                    typ, val, tb = sys.exc_info()
                    try:
                        logger.exception("prepareContents")

                        exc_lines = traceback.format_exception( typ,
                                                                val,
                                                                tb )
                        ob = BadFile( name,
                                      entry_filepath,
                                      exc_str='\r\n'.join(exc_lines),
                                      fullname=entry )
                    finally:
                        tb = None   # Avoid leaking frame!

                # FS-based security
                permissions = metadata.getSecurity()
                if permissions is not None:
                    for name in permissions.keys():
                        acquire, roles = permissions[name]
                        try:
                            ob.manage_permission(name,roles,acquire)
                        except ValueError:
                            logger.exception("Error setting permissions")
###########################################################################
# This is the monkeypatch. These lines don't exist in CMFCore.  This allows
# unauthenticated users to access filesystem-based resources like page
# templates and static UI elements.
###########################################################################
                else:
                    ob.manage_permission('View',('Authenticated',),1)
###########################################################################
# End monkeypatch
###########################################################################

                # only DTML Methods and Python Scripts can have proxy roles
                if hasattr(ob, '_proxy_roles'):
                    try:
                        ob._proxy_roles = tuple(metadata.getProxyRoles())
                    except Exception:
                        logger.exception("Error setting proxy role")

                ob_id = ob.getId()
                data[ob_id] = ob
                objects.append({'id': ob_id, 'meta_type': ob.meta_type})

    return data, tuple(objects)
