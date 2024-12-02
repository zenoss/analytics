##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from AccessControl import Permissions

from Products.ZenRelations.RelSchema import ToManyCont, ToOne

from .MibBase import MibBase


class MibNotification(MibBase):
    objects = []

    _properties = MibBase._properties + (
        {"id": "objects", "type": "lines", "mode": "w"},
    )

    _relations = MibBase._relations + (
        (
            "module",
            ToOne(ToManyCont, "Products.ZenModel.MibModule", "notifications"),
        ),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            "immediate_view": "viewMibNotification",
            "actions": (
                {
                    "id": "overview",
                    "name": "Overview",
                    "action": "viewMibNotification",
                    "permissions": (Permissions.view,),
                },
            ),
        },
    )
