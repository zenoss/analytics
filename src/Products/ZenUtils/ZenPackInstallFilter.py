##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import Interface


class IZenPackInstallFilter(Interface):

    def installable(pack_name):
        """Given a zenpack name of the form `A.B.C`, return a bool determining
        if it is installable or not"""


class ZenPackInstallFilter(object):
    """ A zenpack install filterer that provides simple blacklisting
    based on zenpack name only.
    In the future, it can be enhanced to support specifying zenpack versions
    as well as Zenoss versions and whitelisting """

    def __init__(self):
        self.deny = set([
            'ZenPacks.zenoss.WebScale',
            'ZenPacks.zenoss.AutoTune',
        ])

    def installable(self, pack_name):
        return pack_name not in self.deny

