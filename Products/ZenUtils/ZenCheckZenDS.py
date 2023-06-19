#!/opt/zenoss/bin/python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import argparse
import atexit
import logging
import os
import re
import subprocess
from subprocess import Popen, PIPE
import sys

from Products.ZenUtils.config import ConfigFile
from Products.ZenUtils.configlog import ZenRotatingFileHandler
from Products.ZenUtils.path import zenPath

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("zen.zencheckzends")
LOG.addHandler(ZenRotatingFileHandler("zencheckzends.log",
                                      maxBytes=10 * 1024 * 1024,
                                      backupCount=3))


class Main(object):

    def __init__(self, options):
        self.options = options

    def install(self, silent=False):
        databases = self.options.databases
        if not databases: databases = self._zodb_databases()
        script = zenPath("Products", "ZenUtils", "relstorage", "mysql", "003.sql")
        with open(script, 'r') as f: sql = f.read()
        for database in databases:

            check_sql = """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND UPPER(table_name) = 'CONNECTION_INFO';
            """

            stdout, stderr = self._zendb(database, check_sql)
            try:
                if int(stdout) > 0:
                    if not silent:
                        LOG.info("Database already has %s.connection_info table. No action required." % (database,))
                else:
                    stdout, stderr = self._zendb(database, sql)
                    if not silent:
                        LOG.warn("Created %s.connection_info table in database. PLEASE RESTART ALL DEPENDENT SERVICES." % (database,))
            except ValueError:
                if not silent:
                    LOG.error("Unable to determine if %s.connection_info table exists in database!" % (database,))
                exit(1)

        check_sql = """
        SELECT COUNT(*)
        FROM information_schema.routines
        WHERE UPPER(routine_schema) = 'MYSQL'
        AND UPPER(routine_name) = 'KILLTRANSACTIONS';
        """

        sql = """
        DROP PROCEDURE IF EXISTS mysql.KillTransactions;
        DELIMITER $$
        CREATE PROCEDURE mysql.KillTransactions(IN num_seconds int(10) unsigned, IN action varchar(10))
        BEGIN
            DECLARE _ts int;
            DECLARE _q_db longtext;
            DECLARE _q_pid longtext;
            DECLARE _q_info longtext;
            DECLARE _q_outer_joins longtext;
            DECLARE done BOOL DEFAULT FALSE;
            DECLARE v_db varchar(64);
            DECLARE _txns_count INT DEFAULT 0;
            DECLARE _txns_killed TEXT DEFAULT "'HOST','DB','COMMAND','STATE','INFO','PID','LINE1','LINE2','TRX_ID','TRX_QUERY','TRX_STARTED','TRX_MYSQL_THREAD_ID'";
            DECLARE v_host varchar(54);
            DECLARE v_command varchar(16);
            DECLARE v_state varchar(64);
            DECLARE v_info longtext;
            DECLARE v_pid bigint(21) unsigned;
            DECLARE v_line1 varchar(1000);
            DECLARE v_line2 varchar(1000);
            DECLARE v_trx_id varchar(20);
            DECLARE v_trx_query varchar(1024);
            DECLARE v_started varchar(20);
            DECLARE v_thread_id bigint(21) unsigned;
            DECLARE c_db CURSOR FOR
              SELECT DISTINCT p.db
              FROM information_schema.innodb_trx trx
              INNER JOIN information_schema.processlist p
                ON p.id = trx.trx_mysql_thread_id
              WHERE (_ts - unix_timestamp(trx.trx_started)) > num_seconds;
            DECLARE c_thread_id CURSOR FOR
              SELECT *
              FROM long_transactions
              WHERE (_ts - unix_timestamp(trx_started)) > num_seconds;
            DECLARE CONTINUE HANDLER FOR SQLSTATE '02000' SET done = TRUE;
            SET done = FALSE;
            SET _ts = unix_timestamp();
            OPEN c_db;
            REPEAT
              FETCH c_db INTO v_db;
              IF NOT done AND EXISTS(SELECT 1
                                        FROM information_schema.columns
                                        WHERE table_schema = v_db
                                        AND UPPER(table_name) = 'CONNECTION_INFO')
              THEN
                SET _q_db = CONCAT('`',REPLACE(v_db,'`','``'),'`');
                SET _q_pid = CONCAT_WS(', ', _q_pid,
                  CONCAT(_q_db, '.connection_info.pid'));
                SET _q_info = CONCAT_WS(', ', _q_info,
                  CONCAT(_q_db, '.connection_info.info'));
                SET _q_outer_joins = CONCAT_WS(' ', _q_outer_joins,
                  CONCAT('LEFT OUTER JOIN ',
                         _q_db,
                         '.connection_info on p.id = ',
                         _q_db,
                         '.connection_info.connection_id and p.db = ',
                         QUOTE(v_db)));
              END IF;
            UNTIL done END REPEAT;

            SET @query = CONCAT('
              CREATE OR REPLACE VIEW
              long_transactions
              AS
              SELECT
                p.host,
                p.db,
                p.command,
                p.state,
                p.info,
                coalesce(', coalesce(_q_pid,'NULL'), ') as pid,
                substring_index(coalesce(', coalesce(_q_info,'NULL'), '),''\n'',1) as line1,
                substring_index(substring_index(coalesce(', coalesce(_q_info,'NULL'), '),''\n'',2),''\n'',-1) as line2,
                trx.trx_id,
                trx.trx_query,
                trx.trx_started,
                trx.trx_mysql_thread_id
              FROM information_schema.innodb_trx trx
              INNER JOIN information_schema.processlist p
                ON p.id = trx.trx_mysql_thread_id ',
              coalesce(_q_outer_joins,''));
            PREPARE stmt FROM @query;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            SET done = FALSE;
            OPEN c_thread_id;
            REPEAT
              FETCH c_thread_id
              INTO
                  v_host,
                  v_db,
                  v_command,
                  v_state,
                  v_info,
                  v_pid,
                  v_line1,
                  v_line2,
                  v_trx_id,
                  v_trx_query,
                  v_started,
                  v_thread_id;
              IF NOT done THEN
                SET _txns_killed = CONCAT_WS('\n', _txns_killed, CONCAT_WS(',',
                    QUOTE(v_host),
                    QUOTE(coalesce(v_db,'')),
                    QUOTE(v_command),
                    QUOTE(coalesce(v_state,'')),
                    QUOTE(coalesce(v_info,'')),
                    QUOTE(coalesce(v_pid,'')),
                    QUOTE(coalesce(v_line1,'')),
                    QUOTE(coalesce(v_line2,'')),
                    QUOTE(v_trx_id),
                    QUOTE(coalesce(v_trx_query,'')),
                    QUOTE(v_started),
                    QUOTE(v_thread_id)));
                IF 'KILL' = upper(action) THEN
                  KILL v_thread_id;
                END IF;
                SET _txns_count = _txns_count + 1;
              END IF;
            UNTIL done END REPEAT;
            IF _txns_count < 1 THEN
              SET _txns_killed = 'None';
            END IF;
            SELECT _txns_killed;
        END
        $$
        DELIMITER ;
        DROP EVENT IF EXISTS kill_long_running_txns;
        """

        stdout, stderr = self._zendb('mysql', check_sql)
        try:
            if int(stdout) > 0:
                if not silent:
                    LOG.info("Database already has mysql.KillTransactions stored procedure. No action required.")
            else:
                stdout, stderr = self._zendb('mysql', sql)
                if not silent:
                    LOG.info("Created mysql.KillTransactions stored procedure.")
        except ValueError:
            if not silent:
                LOG.error("Unable to determine if mysql.KillTransactions stored procedure exists in database!")
            exit(1)

    def check(self):
        sql = "call mysql.KillTransactions(%d,'DRYRUN');" % (self.options.minutes * 60,)
        stdout, stderr = self._zendb('mysql', sql)
        stdout = stdout.strip()
        if stdout != "None":
            lines = re.split("\\\\n",stdout)
            for line in lines:
                LOG.info("FOUND: %s", line)

    def truncate(self):
        databases = self.options.databases
        if not databases: databases = self._zodb_databases()
        for database in databases:
            sql = "truncate {0}.{1}".format(database, 'connection_info')
            stdout, stderr = self._zendb(database, sql)

    def kill(self):
        sql = "call mysql.KillTransactions(%d,'KILL');" % (self.options.minutes * 60,)
        stdout, stderr = self._zendb('mysql', sql)
        stdout = stdout.strip()
        if stdout != "None":
            lines = re.split("\\\\n",stdout)
            for line in lines:
                LOG.warn("KILLED: %s", line)

    def _globalConfSettings(self):
        zenhome = os.environ.get('ZENHOME')
        if zenhome:
            with open(os.path.join(zenhome, 'etc/global.conf'), 'r') as fp:
                globalConf = ConfigFile(fp)
                settings = {}
                for line in globalConf.parse():
                    if line.setting:
                        key, val = line.setting
                        settings[key] = val
                return settings

    def _zodb_databases(self):
        settings = self._globalConfSettings()
        zodb = settings.get('zodb-db','zodb')
        zodb_session = zodb + "_session"
        return [zodb, zodb_session]

    def _zendb(self, db_name, sql):
        settings = self._globalConfSettings()
        db_type = settings.get('zodb-db-type','mysql')
        if not db_type == 'mysql':
            LOG.error('%s is not a valid database type.' % dbType)
            sys.exit(1)
        db_host = self.options.hostname or settings.get('zodb-host',None) or settings.get('host',None)
        if not db_host:
            LOG.error('ZODB database hostname not found in global.conf nor on the command line')
            sys.exit(1)
        db_port = self.options.port or settings.get('zodb-port',None) or settings.get('port',None)
        if not db_port:
            LOG.error('ZODB database port not found in global.conf nor on the command line')
            sys.exit(1)
        env = os.environ.copy()
        db_user = self.options.username or settings.get('zodb-admin-user',None) or 'root'
        db_pass = env.get('MYSQL_PWD',None) or settings.get('zodb-admin-password',None) or ''
        env['MYSQL_PWD'] = db_pass
        cmd = ['mysql',
               '--batch',
               '--skip-column-names',
               '--user=%s' % db_user,
               '--host=%s' % db_host,
               '--port=%s' % db_port,
               '--database=%s' % db_name]
        s = Popen(cmd, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        try:
          stdout, stderr = s.communicate(sql)
          rc = s.wait()
          if rc:
              LOG.error("Error executing mysql: %s %s\n" % (stdout, stderr))
              sys.exit(1)
          else:
              return (stdout, stderr)
        except KeyboardInterrupt:
          subprocess.call('stty sane', shell=True)
          s.kill()


def _get_lock(process_name):

    # Should we find a better place for lock?
    lock_name = "%s.lock" % process_name
    lock_path = os.path.join('/tmp', lock_name)

    if os.path.isfile(lock_path):
        LOG.error("'%s' lock already exists - exiting" % (process_name))
        return False
    else:
        file(lock_path, "w+").close()
        atexit.register(os.remove, lock_path)
        LOG.debug("Acquired '%s' execution lock" % (process_name))
        return True


if __name__ == "__main__":

    if not _get_lock('zencheckzends'):
        sys.exit(1)

    epilog = "Checks for (or kills) long-running database transactions."
    parser = argparse.ArgumentParser(epilog=epilog)
    parser.add_argument("action", type=str,
        choices=["install", "install-silent", "check", "kill", "truncate"],
        help="user action to operate with long-running database transactions.")
    parser.add_argument("-m", "--minutes",
        dest="minutes", default=360, type=int,
        help='minutes before a transaction is considered "long-running"')
    parser.add_argument("-d", "--database",
        dest="databases", default=[], action="append",
        help='which database to use. ("-d foo -d bar" for multiple databases)')
    parser.add_argument("-u", "--username",
        dest="username", default=None,
        help='username of admin user for database server (probably "root")')
    parser.add_argument("--hostname",
        dest="hostname", default=None,
        help='hostname of database server')
    parser.add_argument("-p", "--port",
        dest="port", default=None,
        help='port that database server listens on')
    args = parser.parse_args()

    action = args.action
    if action == 'install':
        Main(options=args).install()
    elif action == 'install-silent':
        Main(options=args).install(silent=True)
    elif action == 'check':
        Main(options=args).check()
    elif action == 'kill':
        Main(options=args).kill()
    elif action == 'truncate':
        Main(options=args).truncate()
    else:
        # Something DEFINELY went wrong
        parser.print_usage()
        sys.exit(1)
