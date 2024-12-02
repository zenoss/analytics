##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

import attr

from attr.validators import instance_of
from enum import IntEnum

from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)

log = logging.getLogger("zen.{}".format(__name__.split(".")[-1].lower()))


class InvalidationCause(IntEnum):
    """An enumeration of reasons for the invalidation."""

    Removed = 1
    Updated = 2


@attr.s(frozen=True, slots=True)
class Invalidation(object):
    """Contains the OID and the entity referenced by the OID."""

    oid = attr.ib(validator=instance_of(str))
    entity = attr.ib(validator=instance_of(PrimaryPathObjectManager))
    reason = attr.ib(validator=instance_of(InvalidationCause))
