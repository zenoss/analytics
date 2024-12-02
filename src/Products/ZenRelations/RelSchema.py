##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

RELMETATYPES = (
    "ToOneRelationship",
    "ToManyContRelationship",
    "ToManyRelationship",
)


class RelSchema:
    def __init__(self, remoteType, remoteClass, remoteName):
        self.remoteType = remoteType
        self.remoteClass = remoteClass
        self.remoteName = remoteName

    def createRelation(self, name):
        return self._relationClass(name)

    def checkType(self, relationship):
        """Check that a relationship instance is of correct type"""
        return isinstance(relationship, self._relationClass)


class ToOne(RelSchema):
    from .ToOneRelationship import ToOneRelationship

    _relationClass = ToOneRelationship


class ToMany(RelSchema):
    from .ToManyRelationship import ToManyRelationship

    _relationClass = ToManyRelationship


class ToManyCont(RelSchema):
    from .ToManyContRelationship import ToManyContRelationship

    _relationClass = ToManyContRelationship
