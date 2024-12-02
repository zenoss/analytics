##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface
from zope.viewlet.interfaces import IViewlet, IViewletManager

from Products.ZenUI3.utils.interfaces import IJavaScriptSnippetManager


class IMainSnippetManager(IJavaScriptSnippetManager):
    """
    A viewlet manager to handle general javascript snippets.
    """


class IJavaScriptSrcManager(IViewletManager):
    """
    a viewlet manager to handle java script src viewlets
    """


class ICSSSrcManager(IViewletManager):
    """
    a viewlet manager to handle java script src viewlets
    """


class IXTraceSrcManager(IViewletManager):
    """
    a viewlet manager to handle java script src viewlets that are
    needed for graph visualizations
    """


class IJavaScriptSrcViewlet(IViewlet):
    """
    A viewlet that will generate java a script src file includes
    """


class ICSSSrcViewlet(IViewlet):
    """
    A viewlet that will generate java a script src file includes
    """


class IJavaScriptBundleViewlet(IViewlet):
    """
    A viewlet that will generate a list of CSS link file includes
    """


class ICSSBundleViewlet(IViewlet):
    """
    A viewlet that will generate a list of CSS link file includes
    """


class IHeadExtraManager(IViewletManager):
    """
    A viewlet manager to allow ZenPacks, etc. to plug in extra stuff.
    """


class INewPath(Interface):
    """
    Translates old paths into new ones.
    """


class IErrorMessage(Interface):
    """
    A 404 or 500 page.
    """
