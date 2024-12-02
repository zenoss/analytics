##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""PostgresqlZodbFactory
"""

import logging
log = logging.getLogger("zen.PostgresqlZodbFactory")

import optparse
from zope.interface import implements
import ZODB
import relstorage.storage 
import relstorage.adapters.postgresql
import relstorage.options

import psycopg2 as db_exceptions

from Products.ZenUtils.GlobalConfig import globalConfToDict
from Products.ZenUtils.ZodbFactory import IZodbFactory

def _getDefaults(options=None):
    if options is None:
       o = globalConfToDict()
    else:
       o = options
    settings = {
        'host': o.get('zodb-host', "localhost"),
        'port': o.get('zodb-port', 5432),
        'user': o.get('zodb-user', 'zenoss'),
        'password': o.get('zodb-password', 'zenoss'),
        'dbname': o.get('zodb-db', 'zodb'),
    }
    if 'zodb-socket' in o:
        settings['socket'] = o['zodb-socket']
    return settings


class PostgresqlZodbFactory(object):
    implements(IZodbFactory)

    # set db specific here to allow more flexible imports
    exceptions = db_exceptions
 
 
    def getZopeZodbConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        dsn = []
        keys = ['host', 'port', 'socket', 'user', 'password', 'dbname']
        for key in keys:
            if key in settings:
                dsn.append("%s=%s" % (key, settings[key],))
       
        stanza = "\n".join([ 
            "<postgresql>",
            "    dsn %s" % (" ".join(dsn),),
            "</postgresql>\n",
        ])
        return stanza

    def getConnection(self, **kwargs):
        """Return a ZODB connection."""
        connectionParams =  _getDefaults(kwargs)
        kwargs = {
            'cache_module_name':'memcache',
            'keep_history': kwargs.get('zodb_keep_history', False)
        }
        adapter = relstorage.adapters.postgresql.PostgreSQLAdapter(
             dsn="dbname=%(dbname)s port=%(port)s user=%(user)s password=%(password)s" % connectionParams,
             options=relstorage.options.Options(**kwargs))

        # rename the cache_servers option to not have the zodb prefix.
        if 'zodb_cacheservers' in kwargs:
            kwargs['cache_servers'] = kwargs['zodb_cacheservers']

        storage = relstorage.storage.RelStorage(adapter, **kwargs)
        cache_size = kwargs.get('zodb_cachesize', 1000)
        db = ZODB.DB(storage, cache_size=cache_size)
        return db, storage

    def buildOptions(self, parser):
        """build OptParse options for ZODB connections"""
        group = optparse.OptionGroup(parser, "ZODB Options",
            "ZODB connection options and PostgreSQL Adapter options.")
        group.add_option('-R', '--zodb-dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")
        group.add_option('--zodb-cachesize',
                    dest="zodb_cachesize",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        group.add_option('--zodb-host',
                    dest="zodb_host",default="localhost",
                    help="hostname of the PostgreSQL server for ZODB")
        group.add_option('--zodb-port',
                    dest="zodb_port", type="int", default=5432,
                    help="port of the PostgreSQL server for ZODB")
        group.add_option('--zodb-user', dest='zodb_user', default='zenoss',
                    help='user of the PostgreSQL server for ZODB')
        group.add_option('--zodb-password', dest='zodb_password', default='zenoss',
                    help='password of the PostgreSQL server for ZODB')
        group.add_option('--zodb-db', dest='zodb_db', default='zodb',
                    help='Name of database for PostgreSQL object store')
        # TODO: implement passing socket option to PostgreSQL adapter
        group.add_option('--zodb-socket', dest='zodb_socket', default=None,
                    help='Name of socket file for PostgreSQL server connection if host is localhost')
        group.add_option('--zodb-cacheservers', dest='zodb_cacheservers', default="",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        parser.add_option_group(group)
