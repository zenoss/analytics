##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
"""
This module patches relstorage.adapters.mysql.MySQLdbConnectionManager to
record the process ID and (python) thread ID to the connection_info database
table every time open() is called.
"""

import os
import sys
import thread
import logging
import traceback
import time
from Products.ZenUtils.Utils import monkeypatch
from MySQLdb import OperationalError

TRIM_TIME = time.time()

LOG = logging.getLogger("zen.relstorage.mysql")

_record_pid_sql = (
    "INSERT INTO connection_info (connection_id, pid, info, ts) VALUES (connection_id(), %s, %s, current_timestamp) "
    "ON DUPLICATE KEY UPDATE pid=%s, info=%s, ts=current_timestamp")

_trim_sql = (
    "DELETE ci FROM connection_info AS ci \
    LEFT JOIN information_schema.innodb_trx \
    ON ci.connection_id = information_schema.innodb_trx.trx_mysql_thread_id \
    LEFT JOIN information_schema.processlist \
    ON ci.connection_id = information_schema.processlist.id \
    AND information_schema.processlist.db = DATABASE() \
    WHERE information_schema.innodb_trx.trx_mysql_thread_id IS NULL AND information_schema.processlist.id IS NULL;")

READ_ONLY_TRANSACTION_ERROR = 1792

def trim_db(conn, cursor):
    try:
        conn.autocommit(True)
        cursor.execute(_trim_sql)
    except OperationalError as ex:
        code, msg = ex.args
        if code != READ_ONLY_TRANSACTION_ERROR:
            LOG.debug("Unable to record pid and thread_id to connection_info",
                exc_info=True)
    except Exception:
        LOG.error("Unable to trim data in the connection_info table",
                exc_info=True)
    finally:
        conn.autocommit(False)

def record_pid(conn, cursor):
    try:
        conn.autocommit(True)
        pid = os.getpid()
        tid = thread.get_ident()
        cmd = ' '.join(sys.argv)
        stacktrace = ''.join(traceback.format_stack())
        info = "pid=%d tid=%d\n%s\n%s" % (pid, tid, cmd, stacktrace)
        cursor.execute(_record_pid_sql, (pid, info, pid, info))
    except OperationalError as ex:
        code, msg = ex.args
        if code != READ_ONLY_TRANSACTION_ERROR:
            LOG.debug("Unable to record pid and thread_id to connection_info",
                exc_info=True)
    except Exception:
        LOG.debug("Unable to record pid and thread_id to connection_info",
                 exc_info=True)
    finally:
        conn.autocommit(False)

try:
    from relstorage.adapters.mysql.schema import MySQLSchemaInstaller
    @monkeypatch('relstorage.adapters.mysql.connmanager.MySQLdbConnectionManager')
    def open(self, *args, **kwargs):
        global TRIM_TIME
        conn, cursor = original(self, *args, **kwargs)
        record_pid(conn, cursor)
        if time.time() > (TRIM_TIME + 24*60*60):
            TRIM_TIME = time.time()
            trim_db(conn, cursor)
        return conn, cursor

    @monkeypatch('relstorage.adapters.mysql.connmanager.MySQLdbConnectionManager')
    def close(self, conn=None, cursor=None):
        try:
            if conn is not None and cursor is not None:
                sql = "DELETE FROM connection_info WHERE connection_id = connection_id();"
                cursor.execute(sql)
                conn.commit()
        except Exception:
            pass
        original(self, conn=conn, cursor=cursor)

    @monkeypatch('relstorage.adapters.mysql.schema.MySQLSchemaInstaller')
    def create(self, cursor):
        super(MySQLSchemaInstaller, self).create(cursor)
        self.create_connection_info(cursor)

    @monkeypatch('relstorage.adapters.mysql.schema.MySQLSchemaInstaller')
    def update_schema(self, cursor, tables):
        super(MySQLSchemaInstaller, self).update_schema(cursor, tables)
        if not "connection_info" in tables:
            self.create_connection_info(cursor)

    @monkeypatch('relstorage.adapters.mysql.schema.MySQLSchemaInstaller')
    def create_connection_info(self, cursor):
        script = """
            CREATE TABLE IF NOT EXISTS connection_info(
            connection_id INT NOT NULL,
            pid INT NOT NULL,
            info VARCHAR(60000) NOT NULL,
            ts TIMESTAMP NOT NULL,
            PRIMARY KEY(connection_id),
            KEY(pid)
          ) ENGINE = InnoDB;
        """
        self.runner.run_script(cursor, script)

except ImportError:
    pass
