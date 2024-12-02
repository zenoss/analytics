##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import sys

from Products.ZenRelations.Exceptions import ZenSchemaError
from Products.ZenRelations.utils import importClass, importClasses

logging.basicConfig()
root = logging.getLogger()
root.setLevel(logging.CRITICAL)


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


def checkRelationshipSchema(cls, baseModule):
    """
    Walk all relationship schema definitions and confirm that they
    have reciprical peers on the remote class.
    """
    for relname, rel in cls._relations:
        try:
            remoteClass = importClass(rel.remoteClass, None)
        except AttributeError:
            logging.critical(
                "RemoteClass '%s' from '%s.%s' not found",
                rel.remoteClass,
                cls.__name__,
                relname,
            )
            continue
        try:
            rschema = lookupSchema(remoteClass, rel.remoteName)
        except ZenSchemaError:
            logging.critical(
                "Inverse def '%s' for '%s.%s' not found on '%s'",
                rel.remoteName,
                cls.__name__,
                relname,
                rel.remoteClass,
            )
            continue
        except Exception as e:
            logging.critical(
                "RemoteClass '%s' for '%s.%s' problem.",
                rel.remoteName,
                cls.__name__,
                relname,
            )
            logging.critical(e)
            continue
        try:
            localClass = importClass(rschema.remoteClass, None)
        except AttributeError as e:
            logging.critical(e)
        if not issubclass(cls, localClass):
            logging.critical(
                "Inverse def '%s' from '%s.%s' wrong " "remoteClass: '%s'",
                rel.remoteName,
                cls.__name__,
                relname,
                rschema.remoteClass,
            )
        if rschema.remoteName != relname:
            logging.critical(
                "Inverse def '%s' from '%s.%s' wrong " "remoteName: '%s'",
                rel.remoteName,
                cls.__name__,
                relname,
                rschema.remoteName,
            )
        if rel.remoteType != rschema.__class__:
            logging.critical(
                "'%s.%s' inverse '%s' type %s != %s",
                cls.__name__,
                relname,
                rel.remoteName,
                rschema.__class__.__name__,
                rel.remoteType.__name__,
            )


def main():
    baseModule = None
    if len(sys.argv) > 1:
        baseModule = sys.argv[1].strip()

    if not baseModule:
        print("An argument is required", file=sys.stderr)
        sys.exit(1)

    classList = importClasses(
        basemodule=baseModule, skipnames=("ZentinelPortal", "ZDeviceLoader")
    )

    for classdef in classList:
        if hasattr(classdef, "_relations"):
            logging.info("checking class %s...", classdef.__name__)
            checkRelationshipSchema(classdef, baseModule)
