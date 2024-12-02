##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

from Products.ZenUtils.Security import setupSessionHelper, setupCookieHelper


class SessionAuthentication(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        zport = dmd.zport
        app = zport.unrestrictedTraverse('/')
        # set up dmd users
        setupCookieHelper(zport)
        setupSessionHelper(zport)

        # make sure admin is set up correctly
        setupCookieHelper(app)
        setupSessionHelper(app)

SessionAuthentication()
