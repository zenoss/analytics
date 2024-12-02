##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import io
import optparse
import os
import subprocess
import sys

import six

from .config import ConfigFile

logging.basicConfig()
log = logging.getLogger("zen.zendb")


class ZenDBError(Exception):
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        return repr("ZenDBError: %s" % self.msg)


class ZenDB(object):
    requiredParams = ("db-type", "host", "port", "db", "user")

    def __init__(self, useDefault, dsn=None, useAdmin=False):
        if dsn is None:
            dsn = {}
        self._db = useDefault
        if useDefault in ("zep", "zodb"):
            dbparams = self._getParamsFromGlobalConf(useDefault)
            for setting in dbparams:
                # only override the dsn settings not already specified
                if not dsn.get(setting):
                    if setting in ("user", "password") and useAdmin:
                        # determine if global.conf specifies admin settings
                        key = "admin-" + setting
                        if key in dbparams:
                            dsn[setting] = dbparams[key]
                    else:
                        dsn[setting] = dbparams[setting]

        # check to confirm we have all db params
        for setting in self.requiredParams:
            if not dsn.get(setting):
                raise ZenDBError(
                    "Missing a required DB connection setting "
                    "(%s), and cannot continue. " % setting
                )

        self.dbtype = dsn.pop("db-type")
        if self.dbtype not in ("mysql", "postgresql"):
            raise ZenDBError("%s is not a valid database type." % self.dbtype)
        log.debug("db type: %s", self.dbtype)

        self.dbparams = dsn
        log.debug("connection params: %s", self.dbparams)

    def _getParamsFromGlobalConf(self, defaultDb):
        zenhome = os.environ.get("ZENHOME")
        if not zenhome:
            raise ZenDBError(
                "No $ZENHOME set. In order to use default "
                "configurations, $ZENHOME must point to the "
                "Zenoss install."
            )
        else:
            with io.open(os.path.join(zenhome, "etc/global.conf"), "r") as fp:
                globalConf = ConfigFile(fp)
                settings = {}
                for line in globalConf.parse():
                    if line.setting:
                        key, val = line.setting
                        if key.startswith(defaultDb + "-"):
                            key = key[len(defaultDb) + 1 :]
                            settings[key] = val
                return settings

    def dumpSql(self, outfile=None):
        # output to stdout if nothing passed in, open a file if a string is
        # passed, or use an open file if that's passed in
        if outfile is None:
            outfile = sys.stdout
        elif isinstance(outfile, six.string_types):
            outfile = io.open(outfile, "w")
        else:
            raise ZenDBError(
                "SQL dump output file is invalid. If you passed in a "
                "file name, please confirm that its location is "
                "writable."
            )
        cmd = None
        env = os.environ.copy()
        if self.dbtype == "mysql":
            # TODO: Handle compression of stream (--compress)?
            env["MYSQL_PWD"] = self.dbparams.get("password")
            cmd = [
                "mysqldump",
                "--user=%s" % self.dbparams.get("user"),
                "--host=%s" % self.dbparams.get("host"),
                "--port=%s" % str(self.dbparams.get("port")),
                "--single-transaction",
                self.dbparams.get("db"),
            ]
        elif self.dbtype == "postgresql":
            env["PGPASSWORD"] = self.dbparams.get("password")
            cmd = [
                "pg_dump",
                "--username=%s" % self.dbparams.get("user"),
                "--host=%s" % self.dbparams.get("host"),
                "--port=%s" % self.dbparams.get("port"),
                "--format=p",
                "--no-privileges",
                "--no-owner",
                "--create",
                "--use-set-session-authorization",
                self.dbparams.get("db"),
            ]
        if cmd:
            rc = subprocess.Popen(cmd, stdout=outfile, env=env).wait()  # noqa: S603
            if rc:
                raise subprocess.CalledProcessError(rc, cmd)

    def asynchronousDump(self, file_handler, no_data=False):
        """
        Kick off an SQL dump in the background & return the handler(s) to the
        process(es) which invoked the backup.
        """
        cmd = None
        env = os.environ.copy()
        if self.dbtype == "mysql":
            # TODO: Handle compression of stream (--compress)?
            env["MYSQL_PWD"] = self.dbparams.get("password")
            cmd = [
                "mysqldump",
                "--user=%s" % self.dbparams.get("user"),
                "--host=%s" % self.dbparams.get("host"),
                "--port=%s" % str(self.dbparams.get("port")),
                "--single-transaction",
                "--routines",
                "-p%s" % env["MYSQL_PWD"],
                self.dbparams.get("db"),
            ]

            if no_data:
                cmd.append("--no-data")

            # 1. Kickoff the mysqldump
            ##### Every dump file created using the mysqldump command includes
            ##### a clause named DEFINER.
            ##### Currently, this clause cannot be excluded. If you try to
            ##### restore the dumps on a remote database server or database
            ##### server you would get an error referring to DEFINERS.
            ##### Therefore...
            # 2. Filter out the DEFINERS from the mysqldump
            # 3. Write the filtered mysqldump to a gzip file
            log.debug(cmd)
            mysqldump_process_handle = subprocess.Popen(  # noqa: S603
                cmd, stdout=subprocess.PIPE
            )
            remove_definer_process_handle = subprocess.Popen(  # noqa: S603
                [  # noqa: S607
                    "perl",
                    "-p",
                    "-i.bak",
                    "-e",
                    '"s/DEFINER=\`\w.*\`@\`\d[0-3].*[0-3]\`//g"',
                ],
                stdin=mysqldump_process_handle.stdout,
                stdout=subprocess.PIPE,
            )
            gzip_process_handle = subprocess.Popen(  # noqa: S603
                ["gzip", "-c"],  # noqa: S607
                stdin=remove_definer_process_handle.stdout,
                stdout=file_handler,
            )
            return (mysqldump_process_handle, gzip_process_handle)

    def executeSql(self, sql=None):
        cmd = None
        env = os.environ.copy()
        if self.dbtype == "mysql":
            env["MYSQL_PWD"] = self.dbparams.get("password")
            cmd = [
                "mysql",
                "--batch",
                "--skip-column-names",
                "--user=%s" % self.dbparams.get("user"),
                "--host=%s" % self.dbparams.get("host"),
                "--port=%s" % str(self.dbparams.get("port")),
                "--database=%s" % self.dbparams.get("db"),
            ]
        elif self.dbtype == "postgresql":
            env["PGPASSWORD"] = self.dbparams.get("password")
            cmd = [
                "psql",
                "--quiet",
                "--tuples-only",
                "--username=%s" % self.dbparams.get("user"),
                "--host=%s" % self.dbparams.get("host"),
                "--port=%s" % self.dbparams.get("port"),
                self.dbparams.get("db"),
            ]
        if cmd:
            p = subprocess.Popen(  # noqa: S603
                cmd, env=env, stdin=subprocess.PIPE if sql else sys.stdin
            )
            try:
                if sql:
                    p.communicate(sql)
                rc = p.wait()
                if rc:
                    raise subprocess.CalledProcessError(rc, cmd)
            except KeyboardInterrupt:
                subprocess.call("stty sane", shell=True)  # noqa: S602 S607
                p.kill()


def main():
    parser = optparse.OptionParser()

    # DB connection params
    parser.add_option(
        "--usedb",
        dest="usedb",
        help="Use default connection settings (zodb/zep)",
    )
    parser.add_option(
        "--useadmin",
        action="store_true",
        dest="useadmin",
        help="Use Admin creds from --usedb",
    )
    parser.add_option("--dbtype", dest="dbtype", help="Database Type")
    parser.add_option("--dbhost", dest="dbhost", help="Database Host")
    parser.add_option(
        "--dbport", type="int", dest="dbport", help="Database Port"
    )
    parser.add_option("--dbname", dest="dbname", help="Database Name")
    parser.add_option("--dbuser", dest="dbuser", help="Database User")
    parser.add_option("--dbpass", dest="dbpass", help="Database Password")

    # Usage options
    parser.add_option(
        "--dump", action="store_true", dest="dumpdb", help="Dump database"
    )
    parser.add_option(
        "--dumpfile",
        dest="dumpfile",
        help="Output file for database dump (defaults to STDOUT)",
    )
    parser.add_option(
        "--execsql", dest="execsql", help="SQL to execute (defaults to STDIN)"
    )

    # logging verbosity
    parser.add_option(
        "-v",
        "--logseverity",
        default="INFO",
        dest="logseverity",
        help="Logging severity threshold",
    )

    options, args = parser.parse_args()
    try:
        loglevel = int(options.logseverity)
    except ValueError:
        loglevel = getattr(logging, options.logseverity.upper(), logging.INFO)
    log.setLevel(loglevel)

    try:
        zdb = ZenDB(
            useDefault=options.usedb,
            dsn={
                "db-type": options.dbtype,
                "host": options.dbhost,
                "port": options.dbport,
                "db": options.dbname,
                "user": options.dbuser,
                "password": options.dbpass,
            },
            useAdmin=options.useadmin,
        )

        if options.dumpdb:
            zdb.dumpSql(options.dumpfile)
        else:
            zdb.executeSql(options.execsql)
    except ZenDBError as e:
        log.error(e.msg)
        sys.exit(-1)
    except subprocess.CalledProcessError as e:
        log.error("Error executing command: %r", e.cmd)
        sys.exit(e.returncode)
