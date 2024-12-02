##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "datePush"
##parameters=tagname,defaultDate=None
##bind context=context
##title=Convert the date popup back to a DateTime

import DateTime

request=context.REQUEST
yr = tagname + "_yr"
mo = tagname + "_mo"
dd = tagname + "_dd"
y=request.get(yr,None)
if y:
    m=request.get(mo)
    d=request.get(dd)
    if y and m and d:
        datestring = "%4d/%02d/%02d" % (y, m, d)
        return DateTime.DateTime(datestring)
else:
    return defaultDate
