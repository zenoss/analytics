##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface


class IAuditManager(Interface):
    """
    Announces messages so they can be tracked or handled.
    See __init__.py for usage.
    """

    def audit(
        self,
        category_,  # 'Source.Kind.Action' or ['Source', 'Kind', 'Action']
        object_=None,  # Target object of the specified Kind.
        data_=None,  # New values in format {name:value}
        oldData_=None,  # Old values in format {name:oldValue}
        skipFields_=(),  # Completely ignore fields with these names.
        maskFields_=(),  # Fields to be hidden, such as 'password'.
        **kwargs
    ):  # New values in format name=value
        pass
