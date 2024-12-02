##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
import logging
import sys
import os
from subprocess import Popen, PIPE
from Products.ZenUtils import GlobalConfig

log = logging.getLogger('zen.Migrate')

class ChangeConInfoEngine(Migrate.Step):
    " Change engine for connection_info table. "

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        conf = GlobalConfig.globalConfToDict()
        host = conf.get('zodb-host')
        port = conf.get('zodb-port')
        user = conf.get('zodb-user')
        passwd = conf.get('zodb-password')
        zodb = conf.get('zodb-db','zodb')
        zodb_session = zodb + "_session"

        def zendb(dbname, sql):
             env = os.environ.copy()
             env['MYSQL_PWD'] = passwd
             cmd = ['mysql',
               '--skip-column-names',
               '--user=%s' % user,
               '--host=%s' % host,
               '--port=%s' % port,
               '--database=%s' % dbname]
             s = Popen(cmd, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
             try:
                 stdout, stderr = s.communicate(sql)
                 rc = s.wait()
                 if rc:
                     log.error("Error executing mysql: %s %s\n" % (stdout, stderr))
                 else:
                     return (stdout, stderr)
             except KeyboardInterrupt:
                 subprocess.call('stty sane', shell=True)
                 s.kill()

        for db in [zodb, zodb_session]:

            getEngine = "SELECT count(*) FROM INFORMATION_SCHEMA.TABLES WHERE table_schema = '%s' AND table_name = 'connection_info' and engine != 'InnoDB'" % db
            change_engine = "ALTER TABLE connection_info ENGINE=InnoDB"

            log.info("Checking engine of the connection_info table in %s." % db)
            stdout, stderr = zendb(db, getEngine)
            if stdout and int(stdout) > 0:
                   log.info("Changing engine of connection_info to InnoDB in %s" % db)
                   stdout, stderr = zendb(db, change_engine)


ChangeConInfoEngine()
