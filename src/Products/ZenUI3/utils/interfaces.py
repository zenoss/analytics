##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.viewlet.interfaces import IViewletManager, IViewlet


class IJavaScriptSnippetManager(IViewletManager):
    """
    Simple way to get data from Zope to JavaScript layer. Viewlets deliver up
    bits of raw JavaScript, and the manager wraps them in a SCRIPT tag for the
    template.
    """


class IJavaScriptSnippet(IViewlet):
    """
    Holds raw JavaScript to be delivered to the template by a
    RawJavaScriptManager. Subclass and override the L{snippet} method.
    """

    def snippet():
        """
        Returns a string containing raw javascript to be written to the page.
        Should be independently syntactically sound (i.e., don't forget
        semicolons).
        """
        pass
