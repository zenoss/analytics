##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .ToOneRelationship import ToOneRelationship


def cleanUpRelationships(ob, event):
    """
    Unlinks non-container relationships when their targets are being deleted.
    """
    if getattr(event.object, "_operation", -1) < 1:
        # Don't bother in the case where the other side is a container.
        if not (
            isinstance(ob, ToOneRelationship)
            and ob.remoteTypeName() == "ToManyCont"
        ):
            ob._remoteRemove()


def resetUnderscoreOperation(ob, event):
    """
    Make sure that the _operation attribute on a RelationshipManager is reset
    after paste/move/rename.
    """
    if ob._operation > -1:
        ob._operation = -1
