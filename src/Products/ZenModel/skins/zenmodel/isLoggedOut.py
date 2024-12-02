##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "isUserLoggedOut"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

userName = context.ZenUsers.getUser()

if userName == 'Anonymous User':
    return 'True'
else:
    return 'False'
