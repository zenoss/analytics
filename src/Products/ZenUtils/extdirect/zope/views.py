##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class ExtDirectJsView(BrowserView):
    template = ViewPageTemplateFile('extdirect.js.pt')

    def __call__(self, *args, **kwargs):
        self.request.response.enableHTTPCompression(REQUEST=self.request)
        self.request.response.setHeader('Content-Type', 'text/javascript')
        return self.template()

class JsonApiJsView(BrowserView):
    template = ViewPageTemplateFile('jsonapi.js.pt')

    def __call__(self, *args, **kwargs):
        self.request.response.enableHTTPCompression(REQUEST=self.request)
        self.request.response.setHeader('Content-Type', 'text/javascript')
        return self.template()
