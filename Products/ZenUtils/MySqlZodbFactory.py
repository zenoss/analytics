##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

"""MySqlZodbConnection
"""
import uuid
import logging
log = logging.getLogger("zen.MySqlZodbFactory")

import optparse
import os
import subprocess
from zope.interface import implements
import ZODB
import relstorage.storage
import relstorage.adapters.mysql
import relstorage.options
import _mysql_exceptions as db_exceptions

from Products.ZenUtils.GlobalConfig import globalConfToDict
from Products.ZenUtils.ZodbFactory import IZodbFactory

import memcacheClientWrapper

_DEFAULT_MYSQLPORT = 3306
_DEFAULT_COMMIT_LOCK_TIMEOUT = 30


def _getZendsConfig():
    # Check whether the ZenDS configuration should be used.
    useZends = os.environ.get("USE_ZENDS")
    if useZends != "1":
        return {}
    # Locate the ZenDS configuration file and make sure it exists.
    base = os.environ.get("ZENDSHOME", "/opt/zends")
    if not os.path.isdir(base):
        return {}
    configfile = os.path.join(base, "etc", "zends.cnf")
    if not os.path.exists(configfile):
        return {}
    # Read the client config sections of the configuration file.
    output = subprocess.check_output([
            # The command
            os.path.join(base, "bin", "my_print_defaults"),
            # Specify the config file to read from
            "--defaults-file=%s" % configfile,
            # Specify the relevant config groups
            "mysql", "client"
        ])
    # 'output' is a string of lines having the following pattern:
    #     --<name>=<value>
    # so a dict where <name> maps to <value> is created and returned.
    config = {}
    lines = output.split('\n')
    for opt in (line.split('=') for line in lines):
        config[opt[0][2:]] = opt[1] if len(opt) == 2 else True
    return config
_ZENDS_CONFIG = _getZendsConfig()


def _getDefaults(options=None):
    if options is None:
       o = globalConfToDict()
    else:
       o = options
    settings = {
        'host': o.get('zodb-host', "localhost"),
        'port': o.get(
            'zodb-port', _ZENDS_CONFIG.get("port", _DEFAULT_MYSQLPORT)
        ),
        'user': o.get('zodb-user', 'zenoss'),
        'passwd': o.get('zodb-password', 'zenoss'),
        'db': o.get('zodb-db', 'zodb'),
    }
    if 'zodb-socket' in o:
        settings['unix_socket'] = o['zodb-socket']
    return settings




class MySqlZodbFactory(object):
    implements(IZodbFactory)

    # set db specific here to allow more flexible imports
    exceptions = db_exceptions

    def _getConf(self, settings):
        config = []
        keys = ['host', 'port', 'unix_socket', 'user', 'passwd', 'db']
        for key in keys:
            if key in settings:
                config.append("    %s %s" % (key, settings[key],))

        stanza = "\n".join([
            "<mysql>",
            "\n".join(config),
            "</mysql>\n",
        ])
        return stanza

    def getZopeZodbConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        return self._getConf(settings)

    def getZopeZodbSessionConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        settings['db'] += '_session'
        return self._getConf(settings)

    def getConnection(self, **kwargs):
        """Return a ZODB connection."""
        connectionParams = {
            'host': kwargs.get('zodb_host', "localhost"),
            'port': kwargs.get(
                'zodb_port', _ZENDS_CONFIG.get("port", _DEFAULT_MYSQLPORT)
            ),
            'user': kwargs.get('zodb_user', 'zenoss'),
            'passwd': kwargs.get('zodb_password', 'zenoss'),
            'db': kwargs.get('zodb_db',  'zodb'),
        }
        # Make sure 'port' is an integer
        try:
            connectionParams['port'] = int(connectionParams['port'])
        except (ValueError, TypeError) as e:
            raise ValueError("Invalid 'port' value: %s; %s" % (connectionParams['port'], e))
        socket = kwargs.get('zodb_socket')
        if not socket:
            socket = _ZENDS_CONFIG.get("socket")
        if socket:
            connectionParams['unix_socket'] = socket
        wrappedModuleName = 'wrappedMemcache-' + str(uuid.uuid4())
        memcacheClientWrapper.createModule(wrappedModuleName,
                server_max_value_length = kwargs.get('zodb_cache_max_object_size'))
        relstoreParams = {
            'cache_module_name': wrappedModuleName,
            'keep_history': kwargs.get('zodb_keep_history', False),
            'commit_lock_timeout': kwargs.get(
                'zodb_commit_lock_timeout', _DEFAULT_COMMIT_LOCK_TIMEOUT)
        }
        adapter = relstorage.adapters.mysql.MySQLAdapter(
             options=relstorage.options.Options(**relstoreParams),
             **connectionParams)

        # rename the cache_servers option to not have the zodb prefix.
        cache_servers = kwargs.get('zodb_cacheservers')
        if cache_servers:
            relstoreParams['cache_servers'] = cache_servers

        storage = relstorage.storage.RelStorage(adapter, **relstoreParams)
        cache_size = kwargs.get('zodb_cachesize', 1000)
        db = ZODB.DB(storage, cache_size=cache_size)
        import Globals
        Globals.DB = db
        return db, storage

    def buildOptions(self, parser):
        """build OptParse options for ZODB connections"""
        group = optparse.OptionGroup(parser, "ZODB Options",
            "ZODB connection options and MySQL Adapter options.")
        group.add_option('-R', '--zodb-dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")
        group.add_option('--zodb-cachesize',
                    dest="zodb_cachesize",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        group.add_option('--zodb-host',
                    dest="zodb_host",default="localhost",
                    help="hostname of the MySQL server for ZODB")
        group.add_option('--zodb-port',
                    dest="zodb_port", type="int", default=3306,
                    help="port of the MySQL server for ZODB")
        group.add_option('--zodb-user', dest='zodb_user', default='zenoss',
                    help='user of the MySQL server for ZODB')
        group.add_option('--zodb-password', dest='zodb_password', default='zenoss',
                    help='password of the MySQL server for ZODB')
        group.add_option('--zodb-db', dest='zodb_db', default='zodb',
                    help='Name of database for MySQL object store')
        group.add_option('--zodb-socket', dest='zodb_socket', default=None,
                    help='Name of socket file for MySQL server connection if host is localhost')
        group.add_option('--zodb-cacheservers', dest='zodb_cacheservers', default="",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        group.add_option('--zodb-cache-max-object-size', dest='zodb_cache_max_object_size',
                    default=None, type='int', help='memcached maximum object size in bytes')
        group.add_option(
            '--zodb-commit-lock-timeout',
            dest='zodb_commit_lock_timeout', default=30, type='int',
            help=(
                "Specify the number of seconds a database connection will "
                "wait to acquire a database 'commit' lock before failing "
                "(defaults to 30 seconds if not specified)."
            )
        )
        parser.add_option_group(group)


