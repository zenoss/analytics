##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class AutoString(object):
    """
    For backwards compatibility during upgrades.
    ActionName.BlahBlah yields string 'BlahBlah'.
    ActionTargetType.FooBar yields string 'FooBar'.
    """

    def __getattr__(self, attr):
        return attr


ActionName = ActionTargetType = AutoString()
