##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "logoutUser"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 
req = context.REQUEST
context.acl_users.resetCredentials(req, req.RESPONSE)

req.RESPONSE.expireCookie("_ZopeId", path='/zport')
req.RESPONSE.expireCookie("beaker.session", path='/')
req.RESPONSE.expireCookie("ZAuthToken", path='/')

req.SESSION.clear()


# we want to display logged_out when user is logged in with basic auth
# need to figureout how to do this.
#dest = '/zport/dmd/logged_out'
dest = '/zport/dmd/'
if req.get('HTTP_REFERER') != dest:
    req.RESPONSE.redirect(dest)
return
