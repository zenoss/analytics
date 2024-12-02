##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import cgi
from Products.ZenUtils.extdirect.router import DirectRouter, DirectException


class ZopeDirectRouter(DirectRouter):
    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def __call__(self):
        # Allow only requests with application/json content type as text/plain
        # content type is used for CSRF attacks.
        content_type = self.request.get_header('content-type')
        mimetype, options = cgi.parse_header(content_type)
        if mimetype.lower() != "application/json":
            raise DirectException(
                "Only 'application/json' is supported as content type.")

        body = self.request.get('BODY')
        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.enableHTTPCompression(self.request)
        return super(ZopeDirectRouter, self).__call__(body)
