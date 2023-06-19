#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''zenrestore

Restores a zenoss backup created by zenbackup.
'''

import logging
import sys
import os
import subprocess
import tarfile
import ConfigParser

from ZCmdBase import ZCmdBase
from Products.ZenUtils.path import binPath, zenPath
from Products.ZenUtils.Utils import requiresDaemonShutdown

from ZenBackupBase import *


class ZenRestore(ZenBackupBase):

    def __init__(self):
        ZenBackupBase.__init__(self)
        self.log = logging.getLogger("zenrestore")
        logging.basicConfig()
        if self.options.verbose:
            self.log.setLevel(10)
        else:
            self.log.setLevel(40)

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenBackupBase.buildOptions(self)

        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File from which to restore.')
        self.parser.add_option('--dir',
                               dest="dir",
                               default=None,
                               help='Path to an untarred backup file'
                                        ' from which to restore.')
        self.parser.add_option('--no-zodb',
                               dest="noZODB",
                               default=False,
                               action='store_true',
                               help='Do not restore the ZODB.')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not restore the events database.')
        self.parser.add_option('--no-perfdata',
                               dest="noPerfdata",
                               default=False,
                               action='store_true',
                               help='Do not restore performance data.')
        self.parser.add_option('--deletePreviousPerfData',
                               dest="deletePreviousPerfData",
                               default=False,
                               action='store_true',
                               help='Delete ALL existing performance data before restoring?')
        self.parser.add_option('--zenpacks',
                               dest='zenpacks',
                               default=False,
                               action='store_true',
                               help=('Experimental: Restore any ZenPacks in ' 
                                     'the backup. Some ZenPacks may not work '
                                     'properly. Reinstall ZenPacks if possible'))

    def getSettings(self):
        ''' Retrieve some options from settings file
        We want to take them in the following priority:
            1.  command line
            2.  settings file
            3.  defaults from build options
        '''
        try:
            f = open(os.path.join(self.tempDir, CONFIG_FILE), 'r')
        except Exception:
            return
        try:
            config = ConfigParser.SafeConfigParser()
            config.readfp(f)
            for name, value in config.items(CONFIG_SECTION):
                # If we have a config, then change the default to match the config.
                if name in self.parser.defaults:
                    self.parser.defaults[name] = value
                else:
                    #we don't have that option with a default, so create it now
                    self.parser.add_option('--'+name,
                                           dest=name,
                                        default=value)
            #now reparse the command line to bring in anything the user actually set or the new defaults we created.
            (self.options, self.args) = self.parser.parse_args(args=self.inputArgs)
        finally:
            f.close()
    
    def getSqlFile(self, filename):
        """
        Find path to sql file in backup, trying gzipped versions
        Returns path to real file, or none if nothing found
        """
        pathFile = os.path.join(self.tempDir, filename)
        for path in (pathFile, pathFile + '.gz'):
            if os.path.isfile(path):
                return path
        return None

    def restoreMySqlDb(self, host, port, db, user, passwd, sqlFile, socket=None):
        """
        Create MySQL database if it doesn't exist.
        """
        mysql_cmd = ['mysql', '-u%s' % user]
        mysql_cmd.extend(passwd)
        if host and host != 'localhost':
            mysql_cmd.extend(['--host', host])
            if self.options.compressTransport:
                mysql_cmd.append('--compress')
        if port and str(port) != '3306':
            mysql_cmd.extend(['--port', str(port)])
        if socket:
            mysql_cmd.extend(['--socket', socket])

        mysql_cmd = subprocess.list2cmdline(mysql_cmd)

        cmd = 'echo "create database if not exists %s" | %s' % (db, mysql_cmd)
        os.system(cmd)
        
        sql_path = os.path.join(self.tempDir, sqlFile)
        if sqlFile.endswith('.gz'):
            cmd_fmt = "gzip -dc {sql_path}"
        else:
            cmd_fmt = "cat {sql_path}"
        cmd_fmt += " | {mysql_cmd} {db}"
        cmd = cmd_fmt.format(**locals())
        os.system(cmd)

    @requiresDaemonShutdown('zeneventserver')
    def restoreZEP(self):
        '''
        Restore ZEP DB and indexes
        '''
        zepSql = self.getSqlFile('zep.sql')
        if not zepSql:
            self.msg('This backup does not contain a ZEP database backup.')
            return

        # Setup defaults for db info
        if self.options.fetchArgs:
            self.log.info('Getting ZEP dbname, user, password, port from configuration files.')
            self.readZEPSettings()

        self.msg('Restoring ZEP database.')
        self.restoreMySqlDb(self.options.zepdbhost, self.options.zepdbport,
                            self.options.zepdbname, self.options.zepdbuser,
                            self.getPassArg('zepdbpass'), zepSql)
        self.msg('ZEP database restored.')

        # Remove any current indexes on the system
        index_dir = zenPath('var', 'zeneventserver', 'index')
        if os.path.isdir(index_dir):
            import shutil
            self.msg('Removing existing ZEP indexes.')
            shutil.rmtree(index_dir)

        index_tar = os.path.join(self.tempDir, 'zep.tar')
        if os.path.isfile(index_tar):
            self.msg('Restoring ZEP indexes.')
            zepTar = tarfile.open(os.path.join(self.tempDir, 'zep.tar'))
            zepTar.extractall(zenPath('var'))
            self.msg('ZEP indexes restored.')
        else:
            self.msg('ZEP indexes not found in backup file - will be recreated from database.')

    def hasZeoBackup(self):
        repozoDir = os.path.join(self.tempDir, 'repozo')
        return os.path.isdir(repozoDir)

    def hasSqlBackup(self):
        return bool(self.getSqlFile('zodb.sql'))

    def hasZODBBackup(self):
        return self.hasZeoBackup() or self.hasSqlBackup()

    def restoreZODB(self):
        # Relstorage may have already loaded items into the cache in the
        # initial connection to the database. We have to expire everything
        # in the cache in order to prevent errors with overlapping
        # transactions from the backup.
        if self.options.zodb_cacheservers:
            self.flush_memcached(self.options.zodb_cacheservers.split())
        if self.hasSqlBackup():
            self.restoreZODBSQL()
            self.restoreZODBSessionSQL()
        elif self.hasZeoBackup():
            self.restoreZODBZEO()

    def restoreZODBSQL(self):
        zodbSql = self.getSqlFile('zodb.sql')
        if not zodbSql:
            self.msg('This archive does not contain a ZODB backup.')
            return
        self.msg('Restoring ZODB database.')
        self.restoreMySqlDb(self.options.zodb_host, self.options.zodb_port,
                            self.options.zodb_db, self.options.zodb_user,
                            self.getPassArg('zodb_password'), zodbSql,
                            socket=self.options.zodb_socket)
        self.msg('Done Restoring ZODB database.')

    def restoreZODBSessionSQL(self):
        zodbSessionSql = self.getSqlFile('zodb_session.sql')
        if not zodbSessionSql:
            self.msg('This archive does not contain a ZODB session backup.')
            return
        self.msg('Restoring ZODB session database.')
        self.restoreMySqlDb(self.options.zodb_host, self.options.zodb_port,
                            self.options.zodb_db + "_session",
                            self.options.zodb_user,
                            self.getPassArg('zodb_password'), zodbSessionSql,
                            socket=self.options.zodb_socket)
        self.msg('Done Restoring ZODB session database.')

    def restoreZODBZEO(self):
        repozoDir = os.path.join(self.tempDir, 'repozo')
        tempFilePath = os.path.join(self.tempDir, 'Data.fs')
        tempZodbConvert = os.path.join(self.tempDir, 'convert.conf')

        self.msg('Restoring ZEO backup into MySQL.')

        # Create a Data.fs from the repozo backup
        cmd = []
        cmd.append(binPath('repozo'))
        cmd.append('--recover')
        cmd.append('--repository')
        cmd.append(repozoDir)
        cmd.append('--output')
        cmd.append(tempFilePath)

        rc = subprocess.call(cmd, stdout=PIPE, stderr=PIPE)
        if rc:
            return -1

        # Now we have a Data.fs, restore into MySQL with zodbconvert
        zodbconvert_conf = open(tempZodbConvert, 'w')
        zodbconvert_conf.write('<filestorage source>\n')
        zodbconvert_conf.write('  path %s\n' % tempFilePath)
        zodbconvert_conf.write('</filestorage>\n\n')

        zodbconvert_conf.write('<relstorage destination>\n')
        zodbconvert_conf.write('  <mysql>\n')
        zodbconvert_conf.write('    host %s\n' % self.options.zodb_host)
        zodbconvert_conf.write('    port %s\n' % self.options.zodb_port)
        zodbconvert_conf.write('    db %s\n' % self.options.zodb_db)
        zodbconvert_conf.write('    user %s\n' % self.options.zodb_user)
        zodbconvert_conf.write('    passwd %s\n' % self.options.zodb_password or '')
        if self.options.zodb_socket:
            zodbconvert_conf.write('    unix_socket %s\n' % self.options.zodb_socket)
        zodbconvert_conf.write('  </mysql>\n')
        zodbconvert_conf.write('</relstorage>\n')
        zodbconvert_conf.close()

        rc = subprocess.call(['zodbconvert', '--clear', tempZodbConvert],
                             stdout=PIPE, stderr=PIPE)
        if rc:
            return -1

    def restoreEtcFiles(self):
        self.msg('Restoring config files.')
        cmd = 'cp -p %s %s' % (os.path.join(zenPath('etc'), 'global.conf'), self.tempDir)
        if os.system(cmd): return -1

        cmd = 'tar Cxf %s %s' % (
            zenPath(),
            os.path.join(self.tempDir, 'etc.tar')
        )
        if os.system(cmd): return -1
        if not os.path.exists(os.path.join(zenPath('etc'), 'global.conf')):
            self.msg('Restoring default global.conf')
            cmd = 'mv %s %s' % (os.path.join(self.tempDir, 'global.conf'), zenPath('etc'))
            if os.system(cmd): return -1

    def restoreZenPacks(self):
        self.msg('Restoring ZenPacks.')
        cmd = 'rm -rf %s' % zenPath('ZenPacks')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        zenPath(),
                        os.path.join(self.tempDir, 'ZenPacks.tar'))
        if os.system(cmd): return -1
        # restore bin dir when restoring zenpacks
        #make sure bin dir is in tar
        tempBin = os.path.join(self.tempDir, 'bin.tar')
        if os.path.isfile(tempBin):
            self.msg('Restoring bin dir.')
            #k option prevents overwriting existing bin files
            cmd = ['tar', 'Cxfk', zenPath(),
                   os.path.join(self.tempDir, 'bin.tar')]
            self.runCommand(cmd)
    
    def restoreZenPackContents(self):
        dmd = ZCmdBase(noopts=True).dmd
        self.log.info("Restoring ZenPack contents.")
        for pack in dmd.ZenPackManager.packs():
            pack.restore(self.tempDir, self.log)
        self.log.info("ZenPack contents restored.")

    def restorePerfData(self):
        cmd = 'rm -rf %s' % os.path.join(zenPath(), 'perf')
        if os.system(cmd): return -1
        self.msg('Restoring performance data.')
        cmd = 'tar Cxf %s %s' % (
                        zenPath(),
                        os.path.join(self.tempDir, 'perf.tar'))
        if os.system(cmd): return -1

    def doRestore(self):
        """
        Restore from a previous backup
        """
            
        if self.options.file and self.options.dir:
            sys.stderr.write('You cannot specify both --file and --dir.\n')
            sys.exit(-1)
        elif not self.options.file and not self.options.dir:
            sys.stderr.write('You must specify either --file or --dir.\n')
            sys.exit(-1)
        
        # Maybe check to see if zeo is up and tell user to quit zenoss first
        rootTempDir = ''
        if self.options.file:
            if not os.path.isfile(self.options.file):
                sys.stderr.write('The specified backup file does not exist: %s\n' %
                      self.options.file)
                sys.exit(-1)
            # Create temp dir and untar backup into it
            self.msg('Unpacking backup file')
            rootTempDir = self.getTempDir()
            cmd = 'tar xzfC %s %s' % (self.options.file, rootTempDir)
            if os.system(cmd): return -1
            self.tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        else:
            self.msg('Using %s as source of restore' % self.options.dir)
            if not os.path.isdir(self.options.dir):
                sys.stderr.write('The specified backup directory does not exist:'
                                ' %s\n' % self.options.dir)
                sys.exit(-1)
            self.tempDir = self.options.dir

        # Maybe use values from backup file as defaults for self.options.
        self.getSettings()

        if self.options.zenpacks and not self.hasZODBBackup():
            sys.stderr.write('Archive does not contain ZODB backup; cannot'
                             'restore ZenPacks')
            sys.exit(-1)

        #Check to make sure that zenoss has been stopped
        output = subprocess.Popen(["zenoss", "status"], 
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE
                                  )
        if "pid=" in output.communicate()[0]:
            sys.stderr.write("Please stop all Zenoss daemons and run"
                            "zenrestore again\n")
            sys.exit(-1)
            
        # ZODB
        if self.hasZODBBackup():
            self.restoreZODB()
        else:
            self.msg('Archive does not contain a ZODB backup')

        # Configuration
        self.restoreEtcFiles()

        # ZenPacks
        if self.options.zenpacks:
            tempPacks = os.path.join(self.tempDir, 'ZenPacks.tar')
            if os.path.isfile(tempPacks):
                self.restoreZenPacks()
            else:
                self.msg('Backup contains no ZenPacks.')

        # Allow each installed ZenPack to restore state from the backup
        self.restoreZenPackContents()

        # Performance Data
        tempPerf = os.path.join(self.tempDir, 'perf.tar')
        if os.path.isfile(tempPerf):
            self.restorePerfData()
        else:
            self.msg('Backup contains no perf data.')

        # Events
        if self.options.noEventsDb:
            self.msg('Skipping the events database.')
        else:
            self.restoreZEP()

        # clean up
        if self.options.file:
            self.msg('Cleaning up temporary files.')
            cmd = 'rm -r %s' % rootTempDir
            if os.system(cmd): return -1

        self.msg('Restore complete.')
        # TODO: Audit from command-line without zenpacks loaded.
        # audit('Shell.Backup.Restore', file=self.options.file,
        #       dir=self.options.dir, zenpacks=self.options.zenpacks)
        return 0

    def flush_memcached(self, cacheservers):
        self.msg('Flushing memcached cache.')
        import memcache
        mc = memcache.Client(cacheservers, debug=0)
        mc.flush_all()
        mc.disconnect_all()
        self.msg('Completed flushing memcached cache.')

if __name__ == '__main__':
    zb = ZenRestore()
    if zb.doRestore():
        sys.exit(-1)
