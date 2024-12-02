##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "css_inline_or_link"
##parameters=
##bind container=container
##bind context=context
##bind namespace=_
##bind script=script
##bind subpath=traverse_subpath
##title=Browser detection for stylesheet handling

import string

stylesheet_code = ''

if hasattr(context, 'stylesheet_properties'):
    ag = context.REQUEST.get('HTTP_USER_AGENT', '')
    do_inline_css = 1
    sheet = context.stylesheet_properties.select_stylesheet_id

    if sheet:
        if ag[:9] == 'Mozilla/4' and string.find(ag, 'MSIE') < 0:
            s_obj = getattr(context, sheet)
            s_content = s_obj(None, _, do_inline_css=1)
            stylesheet_code = '<style type="text/css">\n<!--\n %s\n -->\n</style>' % s_content
        else:
            server_url = context.absolute_url_path()
            #took use of portal_url out because its in CMFDefault
            #s_url = '%s/%s' % (context.portal_url(), sheet)
            s_url = '%s/%s' % (server_url, sheet)
            stylesheet_code = '<link rel="stylesheet" href="%s" type="text/css" />' % s_url
return stylesheet_code
