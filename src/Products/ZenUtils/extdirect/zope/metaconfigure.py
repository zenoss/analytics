##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import zope.component
from zope.interface import Interface
from zope.viewlet.metaconfigure import viewletDirective
from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.viewlet.viewlet import ViewletBase
try:
    from Products.Five.browser.metaconfigure import page
except ImportError:
    from zope.publisher.browser.viewmeta import page

from Products.ZenUtils.extdirect.router import DirectProviderDefinition

from interfaces import IExtDirectJavaScriptManager, IJsonApiJavaScriptManager

class SourceViewletBase(ViewletBase):
    _source = ""
    weight=0
    def render(self):
        return self._source

def JavaScriptSourceViewlet(source):
    klass = type('JavaScriptSourceViewlet',
                 (SourceViewletBase,),
                 {'_source':source,
                  'weight':2})
    return klass


allDirectRouters = {}

def directRouter(_context, name, class_, namespace=None, for_=Interface,
                 layer=IDefaultBrowserLayer, timeout="180000", 
                 permission='zenoss.Common'):

    # Register the view at which the class will be available
    page(_context, name, permission, for_, layer, class_=class_)

    # Make a viewlet class with the appropriate javascript source
    definition = DirectProviderDefinition(class_, name, timeout, namespace)

    source = definition.render()
    viewletclass = JavaScriptSourceViewlet(source)
    viewletDirective(_context, name, 'zope2.Public', for_, layer, manager=IExtDirectJavaScriptManager, class_=viewletclass)

    jsonapi_source = definition.render_jsonapi()
    jsonapi_viewletclass = JavaScriptSourceViewlet(jsonapi_source)
    viewletDirective(_context, name, 'zope2.Public', for_, layer, manager=IJsonApiJavaScriptManager, class_=jsonapi_viewletclass)

    # Create a mapping of all of the Zope routers for introspection
    allDirectRouters[class_] = dict(name=name, namespace=namespace, permission=permission)

