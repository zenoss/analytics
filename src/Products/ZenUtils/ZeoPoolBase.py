##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ZeoPoolBase

$Id: ZC.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from threading import Lock

from ZEO import ClientStorage
from ZODB import DB
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from ZenDaemon import ZenDaemon

from Products.ZenUtils.Utils import unused

class ZeoPoolBase(ZenDaemon):
    """
    A multi-threaded daemon that maintains a pool of zeo connections
    that it can hand out to its worker threads.
    """


    def __init__(self, noopts=0, app=None, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        unused(app)
        self.opendb()
        self.openconn = self.getPoolSize()


    def getConnection(self, path=None):
        """Return a connection from the connection pool. If path is passed
        return the object that the path points to.
        """
        with self.poollock:
            if not self.is_connected():
                self.opendb()
            connection=self.db.open()
            root=connection.root()
            app=root['Application']
            self._getContext(app)
            app._p_jar.sync()
            if path:
                return app.getObjByPath(path)
            else:
                return app
            self.openconn -= 1


    def opendb(self):
        addr = (self.options.host, self.options.port)
        self._storage=ClientStorage.ClientStorage(addr)
        self.db=DB(self._storage)
        self.poollock = Lock()


    def closedb(self):
        """Close all connections in both free an inuse pools.
        """
        self.db.close()
        self.db = None
        self._storage = None


    def is_connected(self):
        """Are we connected to zeo.
        """
        return not self._storage or self._storage.is_connected()


    def getPoolSize(self):
        """Return the target max pool size for this database.
        """
        return self.db.getPoolSize()


    def available(self):
        """Return the number of available connection in our pool.
        """
        if self.db._pools:
            pool = self.db._pools[''] # trunk version pool
            return len(pool.available)
        return 0


    def _getContext(self, app):
        resp = HTTPResponse(stdout=None)
        env = {
            'SERVER_NAME':'localhost',
            'SERVER_PORT':'8080',
            'REQUEST_METHOD':'GET'
            }
        req = HTTPRequest(None, env, resp)
        app.__of__(RequestContainer(REQUEST = req))
        return app


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenDaemon.buildOptions(self)
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of zeo server")
        self.parser.add_option('--port',
                    dest="port",type="int", default=8100,
                    help="port of zeo server")
