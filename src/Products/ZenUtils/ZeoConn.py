##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.component import getUtility
from Products.ZenUtils.Utils import set_context
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

class ZeoConn(object):

    def __init__(self, **kwargs):
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        self.db, self.storage = connectionFactory.getConnection(**kwargs)

        self.app = None
        self.dmd = None
        self.opendb()


    def opendb(self):
        if self.app: return
        self.connection=self.db.open()
        root=self.connection.root()
        app = root['Application']
        self.app = set_context(app)
        self.dmd = self.app.zport.dmd


    def syncdb(self):
        self.connection.sync()


    def closedb(self):
        self.connection.close()
        self.db.close()
        self.app = None
        self.dmd = None
