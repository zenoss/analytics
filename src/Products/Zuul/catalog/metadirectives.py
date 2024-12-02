##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from zope.interface import Interface
from zope import schema
from zope.configuration.fields import GlobalObject, Tokens


class IComponentFieldSpecDirective(Interface):
    """
    Registers fields for a component meta_type.
    """
    class_ = GlobalObject(
        title=u"Component Class",
        description=u"The component class for which fields are registered",
        required=True)

    fields = Tokens(
        required=False,
        value_type=schema.TextLine(),
    )
