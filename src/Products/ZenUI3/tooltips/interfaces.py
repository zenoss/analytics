##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import Interface


class ITooltipProvider(Interface):
    """
    A marker interface for utilites that want to provide new/overridden
    pagehelp and tooltop XML to supplement that found in Products/ZenUI3/data.
    """

    def path(self):
        """Return an absolute directory path of pagehelp + tooltip XML.
        The expected file/directory layout is identical to
        Products/ZenUI3/data.

        For example, a valid returned path of
        '/opt/zenoss/ZenPacks/ZenPacks.zenoss.Example/tooltips' might have
        this structure:

            tooltips
            |---en
                |---nav-help.xml
                |---evconsole.xml
        """
        pass
