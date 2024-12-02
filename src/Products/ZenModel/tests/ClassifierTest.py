##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Zope
app = Zope.app()
c = app.dmd.Devices.myClassifier
ce = c.getClassifierEntry({'devicename':'dhcp160','community':'public'})
ce = c.getClassifierEntry({'devicename':'printer','community':'public'})
if ce:
    print "dc path =", ce.getDeviceClassPath
else:
    print 'Failed'
