##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import optparse
import time
import uuid

import MySQLdb
import relstorage.adapters.mysql
import relstorage.options
import relstorage.storage
import ZODB

from zope.interface import implementer

from . import memcacheClientWrapper
from .GlobalConfig import globalConfToDict
from .ZodbFactory import IZodbFactory

_DEFAULT_MYSQLPORT = 3306
_DEFAULT_COMMIT_LOCK_TIMEOUT = 30
_OPERATIONAL_ERROR_RETRY_DELAY = 0.5

log = logging.getLogger("zen.MySqlZodbFactory")


def _getDefaults(options=None):
    o = globalConfToDict() if options is None else options
    settings = {
        "host": o.get("zodb-host", "localhost"),
        "port": o.get("zodb-port", _DEFAULT_MYSQLPORT),
        "user": o.get("zodb-user", "zenoss"),
        "passwd": o.get("zodb-password", "zenoss"),
        "db": o.get("zodb-db", "zodb"),
    }
    if "zodb-socket" in o:
        settings["unix_socket"] = o["zodb-socket"]
    return settings


def _make_exceptions_module():
    import types
    import MySQLdb
    exceptions = types.ModuleType("_mysql_exceptions")
    for ex in (
        MySQLdb.DatabaseError,
        MySQLdb.DataError,
        MySQLdb.IntegrityError,
        MySQLdb.InterfaceError,
        MySQLdb.InternalError,
        MySQLdb.MySQLError,
        MySQLdb.NotSupportedError,
        MySQLdb.OperationalError,
        MySQLdb.ProgrammingError,
    ):
        setattr(exceptions, ex.__name__, ex)
    return exceptions


db_exceptions = _make_exceptions_module()
del _make_exceptions_module


@implementer(IZodbFactory)
class MySqlZodbFactory(object):

    # set db specific here to allow more flexible imports
    exceptions = db_exceptions

    def _getConf(self, settings):
        config = []
        keys = ["host", "port", "unix_socket", "user", "passwd", "db"]
        for key in keys:
            if key in settings:
                config.append("    %s %s" % (key, settings[key],))

        stanza = "\n".join(["<mysql>", "\n".join(config), "</mysql>\n"])
        return stanza

    def getZopeZodbConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        return self._getConf(settings)

    def getZopeZodbSessionConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        settings["db"] += "_session"
        return self._getConf(settings)

    def getConnection(self, **kwargs):
        """Return a ZODB connection."""
        connectionParams = {
            "host": kwargs.get("zodb_host", "localhost"),
            "port": kwargs.get("zodb_port", _DEFAULT_MYSQLPORT),
            "user": kwargs.get("zodb_user", "zenoss"),
            "passwd": kwargs.get("zodb_password", "zenoss"),
            "db": kwargs.get("zodb_db", "zodb"),
        }
        # Make sure 'port' is an integer
        try:
            connectionParams["port"] = int(connectionParams["port"])
        except (ValueError, TypeError) as e:
            raise ValueError(
                "Invalid 'port' value: %s; %s" % (connectionParams["port"], e)
            )
        socket = kwargs.get("zodb_socket")
        if socket:
            connectionParams["unix_socket"] = socket
        wrappedModuleName = "wrappedMemcache-" + str(uuid.uuid4())
        memcacheClientWrapper.createModule(
            wrappedModuleName,
            server_max_value_length=kwargs.get("zodb_cache_max_object_size"),
        )
        relstoreParams = {
            "cache_module_name": wrappedModuleName,
            "keep_history": kwargs.get("zodb_keep_history", False),
            "commit_lock_timeout": kwargs.get(
                "zodb_commit_lock_timeout", _DEFAULT_COMMIT_LOCK_TIMEOUT
            ),
        }
        adapter = relstorage.adapters.mysql.MySQLAdapter(
            options=relstorage.options.Options(**relstoreParams),
            **connectionParams
        )

        # rename the cache_servers option to not have the zodb prefix.
        cache_servers = kwargs.get("zodb_cacheservers")
        if cache_servers:
            relstoreParams["cache_servers"] = cache_servers

        storage = _get_storage(adapter, relstoreParams)
        if storage is None:
            raise SystemExit("Unable to retrieve ZODB storage")

        cache_size = kwargs.get("zodb_cachesize", 1000)
        db = ZODB.DB(storage, cache_size=cache_size)
        import Globals

        Globals.DB = db
        return db, storage

    def buildOptions(self, parser):
        """build OptParse options for ZODB connections"""
        group = optparse.OptionGroup(
            parser,
            "ZODB Options",
            "ZODB connection options and MySQL Adapter options.",
        )
        group.add_option(
            "-R",
            "--zodb-dataroot",
            dest="zodb_dataroot",
            default="/zport/dmd",
            help="root object for data load (i.e. /zport/dmd)",
        )
        group.add_option(
            "--zodb-cachesize",
            dest="zodb_cachesize",
            default=1000,
            type="int",
            help="in memory cachesize default: %default",
        )
        group.add_option(
            "--zodb-host",
            dest="zodb_host",
            default="localhost",
            help="hostname of the MySQL server for ZODB",
        )
        group.add_option(
            "--zodb-port",
            dest="zodb_port",
            type="int",
            default=3306,
            help="port of the MySQL server for ZODB",
        )
        group.add_option(
            "--zodb-user",
            dest="zodb_user",
            default="zenoss",
            help="user of the MySQL server for ZODB",
        )
        group.add_option(
            "--zodb-password",
            dest="zodb_password",
            default="zenoss",
            help="password of the MySQL server for ZODB",
        )
        group.add_option(
            "--zodb-db",
            dest="zodb_db",
            default="zodb",
            help="Name of database for MySQL object store",
        )
        group.add_option(
            "--zodb-socket",
            dest="zodb_socket",
            default=None,
            help="Name of socket file for MySQL server connection "
            "if host is localhost",
        )
        group.add_option(
            "--zodb-cacheservers",
            dest="zodb_cacheservers",
            default="",
            help="memcached servers to use for object cache "
            "(eg. 127.0.0.1:11211)",
        )
        group.add_option(
            "--zodb-cache-max-object-size",
            dest="zodb_cache_max_object_size",
            default=None,
            type="int",
            help="memcached maximum object size in bytes",
        )
        group.add_option(
            "--zodb-commit-lock-timeout",
            dest="zodb_commit_lock_timeout",
            default=30,
            type="int",
            help=(
                "Specify the number of seconds a database connection will "
                "wait to acquire a database 'commit' lock before failing "
                "(defaults to %default seconds if not specified)."
            ),
        )
        parser.add_option_group(group)


def _get_storage(adapter, params):
    attempt = 0
    while attempt < 3:
        try:
            return relstorage.storage.RelStorage(adapter, **params)
        except MySQLdb.OperationalError as ex:
            error = str(ex)
            # Sleep for a very short duration.  Celery signal handlers
            # are given short durations to complete.
            time.sleep(_OPERATIONAL_ERROR_RETRY_DELAY)
            attempt += 1
        except Exception as ex:
            log.exception("unexpected failure")
            # To avoid retrying on unexpected errors, set `attempt` to 3 to
            # cause the loop to exit on the next iteration to allow the
            # "else:" clause to run and cause this worker to exit.
            error = str(ex)
            attempt = 3
    else:
        log.error("failed to initialize ZODB connection: %s", error)
