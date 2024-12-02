##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.Five.viewlet.manager import ViewletManagerBase
from Products.Five.viewlet.viewlet import ViewletBase
from zope.interface import implementer

from .interfaces import IJavaScriptSnippetManager, IJavaScriptSnippet

SCRIPT_TAG_TEMPLATE = """
<script type="text/javascript">
%s
</script>
"""


@implementer(IJavaScriptSnippetManager)
class JavaScriptSnippetManager(ViewletManagerBase):
    def render(self):
        raw_js = "\n".join(v.render() for v in self.viewlets)
        return SCRIPT_TAG_TEMPLATE % raw_js


@implementer(IJavaScriptSnippet)
class JavaScriptSnippet(ViewletBase):
    def snippet(self):
        raise NotImplementedError(
            "Subclasses must implement their own " "snippet method."
        )

    def render(self):
        return self.snippet()
