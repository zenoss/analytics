##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ZenScriptBase

Scripts with classes who extend ZenScriptBase have a zope instance with a
dmd root and loaded ZenPacks, like zendmd.
"""

from zope.component import getUtility

from AccessControl.SecurityManagement import (
    newSecurityManager,
    noSecurityManager,
)
from transaction import commit

from Products.ZenRelations.ZenPropertyManager import setDescriptors

from .CmdBase import CmdBase
from .Exceptions import ZentinelException
from .path import zenPath
from .Utils import getObjByPath, set_context
from .ZodbFactory import IZodbFactoryLookup

defaultCacheDir = zenPath("var")


class DataRootError(Exception):
    pass


class ZenScriptBase(CmdBase):
    def __init__(self, noopts=0, app=None, connect=False, should_log=True):
        CmdBase.__init__(self, noopts, should_log=should_log)
        self.dataroot = None
        self.app = app
        self.db = None
        if connect:
            self.connect()

    def connect(self):
        if not self.app:
            connectionFactory = getUtility(IZodbFactoryLookup).get()
            self.db, self.storage = connectionFactory.getConnection(
                **self.options.__dict__
            )
        self.getDataRoot()
        self.login()
        if getattr(self.dmd, "propertyTransformers", None) is None:
            self.dmd.propertyTransformers = {}
            commit()
        setDescriptors(self.dmd)

    def login(self, name="admin", userfolder=None):
        """Logs in."""
        if userfolder is None:
            userfolder = self.app.acl_users
        user = userfolder.getUserById(name)
        if user is None:
            return
        if not hasattr(user, "aq_base"):
            user = user.__of__(userfolder)
        newSecurityManager(None, user)

    def logout(self):
        """Logs out."""
        noSecurityManager()

    def getConnection(self):
        """Return a wrapped app connection from the connection pool."""
        if not self.db:
            raise ZentinelException(
                "running inside zope can't open connections."
            )
        with self.poollock:
            connection = self.db.open()
            root = connection.root()
            app = root["Application"]
            app = set_context(app)
            app._p_jar.sync()
            return app

    def closeAll(self):
        """Close all connections in both free an inuse pools."""
        self.db.close()

    def opendb(self):
        if self.app:
            return
        self.connection = self.db.open()
        root = self.connection.root()
        app = root["Application"]
        self.app = set_context(app)
        self.app._p_jar.sync()

    def syncdb(self):
        self.connection.sync()

    def closedb(self):
        self.connection.close()
        # self.db.close()
        self.app = None
        self.dataroot = None
        self.dmd = None

    def getDataRoot(self):
        if not self.app:
            self.opendb()
        if not self.dataroot:
            self.dataroot = getObjByPath(self.app, self.options.zodb_dataroot)
            self.dmd = self.dataroot

    def getDmdObj(self, path):
        """Return an object based on a path starting from the dmd"""
        return getObjByPath(self.app, self.options.zodb_dataroot + path)

    def findDevice(self, name):
        """Return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)

    def buildOptions(self):
        """Basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)

        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)
