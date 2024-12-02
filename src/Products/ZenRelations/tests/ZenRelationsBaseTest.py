##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase


class ZenRelationsBaseTest(BaseTestCase):
    """
    Use this class to provide ZenRelations-specific setup, etc., for
    ZenRelations unit tests.
    """

    def build(self, context, klass, id):
        """create instance attache to context and build relationships"""
        return self.create(context, klass, id)
