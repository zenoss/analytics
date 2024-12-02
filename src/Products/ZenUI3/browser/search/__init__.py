##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.Zuul import getFacade
from Products.ZenUI3.browser.javascript import JavaScriptSrcViewlet


class IncludeSearchBox(JavaScriptSrcViewlet):
    """
    Checks for the existence of search providers.  If there are none,
    do not display the query widget.
    """

    path = "/++resource++search/zenoss-search.js"

    def render(self):
        if not getFacade("search").noProvidersPresent():
            return super(IncludeSearchBox, self).render()
        else:
            return ""
