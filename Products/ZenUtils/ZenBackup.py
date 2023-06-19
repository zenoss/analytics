#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''zenbackup

Creates backup of Zope data files, Zenoss conf files and the events database.
'''

import sys
import os
import os.path
from datetime import date
import time
import logging
import ConfigParser
import subprocess
import tarfile
import re
import gzip
from itertools import imap

from ZCmdBase import ZCmdBase
from Products.ZenUtils.path import binPath, zenPath
from Products.ZenUtils.Utils import readable_time
from ZenBackupBase import *
from zope.interface import implements
from Products.Zuul.interfaces import IPreBackupEvent, IPostBackupEvent
from zope.event import notify
from ZenDB import ZenDB


MAX_UNIQUE_NAME_ATTEMPTS = 1000

DEFINER_PATTERN = re.compile(r'/\*((?!/\*).)*DEFINER.*?\*/')

def strip_definer(mysqldump_line):
    """Strips DEFINER statements from mysqldump lines. See ZEN-326."""
    if not mysqldump_line.startswith("/*") or len(mysqldump_line) > 500:
        # speed things up, lines with DEFINER in them 
        #    (1) start with '/*'
        #    (2) are shorter than 500 characters.
        return mysqldump_line
    return DEFINER_PATTERN.sub('', mysqldump_line)

class PreBackupEvent(object):
    implements(IPreBackupEvent)
    def __init__(self, zen_backup_object):
        self._zen_backup_object = zen_backup_object

class PostBackupEvent(object):
    implements(IPostBackupEvent)
    def __init__(self, zen_backup_object):
        self._zen_backup_object = zen_backup_object

class ZenBackupException(Exception):
    def __init__(self, value="", critical=False):
        self.value = value
        self.critical = critical
    def __str__(self):
        return repr(self.value)
    def isCritical(self):
        return self.critical

class ZenBackup(ZenBackupBase):

    def __init__(self, argv):
        # Store sys.argv so we can restore it for ZCmdBase.
        self.argv = argv

        ZenBackupBase.__init__(self)
        self.log = logging.getLogger("zenbackup")
        logging.basicConfig()
        self.log.setLevel(self.options.logseverity)
        
        self._zodb_backup_file_handler = None
        self._zodb_mysqldump_process = None
        self._zodb_backup_gzip_process = None
        
        self._zodb_session_backup_file_handler = None
        self._zodb_session_mysqldump_process = None
        self._zodb_session_backup_gzip_process = None

    def isZeoUp(self):
        '''
        Returns True if Zeo appears to be running, false otherwise.

        @return: whether Zeo is up or not
        @rtype: boolean
        '''
        import ZEO
        zeohome = os.path.dirname(ZEO.__file__)
        cmd = [ binPath('python'),
                os.path.join(zeohome, 'scripts', 'zeoup.py')]
        cmd += '-p 8100 -h localhost'.split()
        self.log.debug("Can we access ZODB through Zeo?")

        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            return False
        return output.startswith('Elapsed time:')

    def saveSettings(self):
        '''
        Save the database credentials to a file for use during restore.
        '''
        config = ConfigParser.SafeConfigParser()
        config.add_section(CONFIG_SECTION)

        config.set(CONFIG_SECTION, 'zodb_host', self.options.zodb_host)
        config.set(CONFIG_SECTION, 'zodb_port', str(self.options.zodb_port))
        config.set(CONFIG_SECTION, 'zodb_db', self.options.zodb_db)
        config.set(CONFIG_SECTION, 'zodb_user', self.options.zodb_user)
        config.set(CONFIG_SECTION, 'zodb_password', self.options.zodb_password)
        if self.options.zodb_socket:
            config.set(CONFIG_SECTION, 'zodb_socket', self.options.zodb_socket)

        config.set(CONFIG_SECTION, 'zepdbhost', self.options.zepdbhost)
        config.set(CONFIG_SECTION, 'zepdbport', self.options.zepdbport)
        config.set(CONFIG_SECTION, 'zepdbname', self.options.zepdbname)
        config.set(CONFIG_SECTION, 'zepdbuser', self.options.zepdbuser)
        config.set(CONFIG_SECTION, 'zepdbpass', self.options.zepdbpass)

        creds_file = os.path.join(self.tempDir, CONFIG_FILE)
        self.log.debug("Writing MySQL credentials to %s", creds_file)
        f = open(creds_file, 'w')
        try:
            config.write(f)
        finally:
            f.close()

    def getDefaultBackupFile(self):
        """
        Return a name for the backup file or die trying.

        @return: unique name for a backup
        @rtype: string
        """
        def getName(index=0):
            """
            Try to create an unique backup file name.

            @return: tar file name
            @rtype: string
            """
            return 'zenbackup_%s%s.tgz' % (date.today().strftime('%Y%m%d'),
                                            (index and '_%s' % index) or '')
        backupDir = zenPath('backups')
        if not os.path.exists(backupDir):
            os.mkdir(backupDir, 0o750)
        for i in range(MAX_UNIQUE_NAME_ATTEMPTS):
            name = os.path.join(backupDir, getName(i))
            if not os.path.exists(name):
                break
        else:
            self.log.critical(
                'Cannot determine an unique file name to use in the backup '
                'directory (%s). Use --outfile to specify location for the '
                'backup file.\n', backupDir)
            sys.exit(-1)
        return name

    def buildOptions(self):
        """
        Basic options setup
        """
        # pychecker can't handle strings made of multiple tokens
        __pychecker__ = 'no-noeffect no-constCond'
        ZenBackupBase.buildOptions(self)
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='Name of file in which the backup will be stored.'
                                     ' Backups will by default be placed'
                                     ' in $ZENHOME/backups/')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not include the events database'
                                    ' in the backup.')
        self.parser.add_option('--no-zodb',
                               dest="noZopeDb",
                               default=False,
                               action='store_true',
                               help='Do not include the ZODB'
                                    ' in the backup.')
        self.parser.add_option('--no-perfdata',
                               dest="noPerfData",
                               default=False,
                               action='store_true',
                               help='Do not include performance data'
                                    ' in the backup.')
        self.parser.add_option('--no-zepindexes',
                               dest='noZepIndexes',
                               default=False,
                               action='store_true',
                               help='Do not include zep indexes in the backup')
        self.parser.add_option('--no-zenpacks',
                               dest="noZenPacks",
                               default=False,
                               action='store_true',
                               help='Do not include ZenPack data'
                                    ' in the backup.')
        self.parser.add_option('--stdout',
                               dest="stdout",
                               default=False,
                               action='store_true',
                               help='Send backup to stdout instead of to a file.')
        self.parser.add_option('--no-save-mysql-access',
                                dest='saveSettings',
                                default=True,
                                action='store_false',
                                help='Do not include zodb and zep credentials'
                                    ' in the backup file for use during restore.')
        self.parser.add_option('--collector',
                               dest="collector",
                               default=False,
                               action='store_true',
                               help='include only data relevant to collector'
                                    ' in the backup.')

        self.parser.remove_option('-v')
        self.parser.add_option('-v', '--logseverity',
                        dest='logseverity',
                        default=20,
                        type='int',
                        help='Logging severity threshold')

    def backupMySqlDb(self, host, port, db, user, passwdType, sqlFile, socket=None, tables=None):
        command = ['mysqldump', '-u%s' %user, '--single-transaction', '--routines']
        credential = self.getPassArg(passwdType)
        database = [db]

        if host and host != 'localhost':
            command.append('-h%s' % host)
            if self.options.compressTransport:
                command.append('--compress')
        if port and str(port) != '3306':
            command.append('--port=%s' % port)
        if socket:
            command.append('--socket=%s' % socket)

        with gzip.open(os.path.join(self.tempDir, sqlFile),'wb') as gf:
            # If tables are specified, backup db schema and data from selected tables.
            if tables is not None:
                self.log.debug(' '.join(command + ['*' * 8] + ['--no-data'] + database))
                schema = subprocess.Popen(command + credential + ['--no-data'] + database,
                    stdout=subprocess.PIPE)
                gf.writelines(imap(strip_definer, schema.stdout))
                schema_rc = schema.wait()
                data_rc = 0
                if tables:
                    self.log.debug(' '.join(command + ['*' * 8] + ['--no-create-info'] + database + tables))
                    data = subprocess.Popen(command + credential + ['--no-create-info'] + database + tables,
                      stdout=subprocess.PIPE)
                    gf.writelines(imap(strip_definer, data.stdout))
                    data_rc = data.wait()
            else:
                self.log.debug(' '.join(command + ['*' * 8] + database))
                schema = subprocess.Popen(command + credential + database,
                    stdout=subprocess.PIPE)
                gf.writelines(imap(strip_definer, schema.stdout))
                schema_rc = schema.wait()

                data_rc = 0

            if schema_rc or data_rc:
                raise ZenBackupException("Backup of (%s) terminated failed." % sqlFile, True)

    def _zepRunning(self):
        """
        Returns True if ZEP is running on the system (by invoking
        zeneventserver status).
        """
        zeneventserver_cmd = zenPath('bin', 'zeneventserver')
        with open(os.devnull, 'w') as devnull:
            return not subprocess.call([zeneventserver_cmd, 'status'], stdout=devnull, stderr=devnull)

    def backupZEP(self):
        '''
        Backup ZEP
        '''
        partBeginTime = time.time()
        
        # Setup defaults for db info
        if self.options.fetchArgs:
            self.log.info('Getting ZEP dbname, user, password, port from configuration files.')
            self.readZEPSettings()

        if self.options.saveSettings:
            self.saveSettings()

        if self.options.noEventsDb:
            self.log.info('Doing a partial backup of the events database.')
            tables=['config','event_detail_index_config','event_trigger','event_trigger_subscription', 'schema_version']
        else:
            self.log.info('Backing up the events database.')
            tables = None

        self.backupMySqlDb(self.options.zepdbhost, self.options.zepdbport,
                           self.options.zepdbname, self.options.zepdbuser,
                           'zepdbpass', 'zep.sql.gz', tables=tables)

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of events database completed in %s.", subtotalTime)

        if not self.options.noEventsDb:
            zeneventserver_dir = zenPath('var', 'zeneventserver')
            if self.options.noZepIndexes:
                self.log.info('Not backing up event indexes.')
            elif self._zepRunning():
                self.log.info('Not backing up event indexes - it is currently running.')
            elif os.path.isdir(zeneventserver_dir):
                self.log.info('Backing up event indexes.')
                zepTar = tarfile.open(os.path.join(self.tempDir, 'zep.tar'), 'w')
                zepTar.add(zeneventserver_dir, 'zeneventserver')
                zepTar.close()
                self.log.info('Backing up event indexes completed.')

    def backupZenPacks(self):
        """
        Backup the zenpacks dir
        """
        #can only copy zenpacks backups if ZEO is backed up
        if not self.options.noZopeDb and os.path.isdir(zenPath('ZenPacks')):
            # Copy /ZenPacks to backup dir
            self.log.info('Backing up ZenPacks.')
            etcTar = tarfile.open(os.path.join(self.tempDir, 'ZenPacks.tar'), 'w')
            etcTar.dereference = True
            etcTar.add(zenPath('ZenPacks'), 'ZenPacks')
            etcTar.close()
            self.log.info("Backup of ZenPacks completed.")
            # add /bin dir if backing up zenpacks
            # Copy /bin to backup dir 
            self.log.info('Backing up bin dir.')
            etcTar = tarfile.open(os.path.join(self.tempDir, 'bin.tar'), 'w')
            etcTar.dereference = True
            etcTar.add(zenPath('bin'), 'bin')
            etcTar.close()
            self.log.info("Backup of bin completed.")
    
    def backupZenPackContents(self):
        dmd = ZCmdBase(noopts=True).dmd
        self.log.info("Backing up ZenPack contents.")
        for pack in dmd.ZenPackManager.packs():
            pack.backup(self.tempDir, self.log)
        self.log.info("Backup of ZenPack contents complete.")
    
    def startBackupZODB(self):
        """
        Backup the Zope database.
        """
        self.log.info('Initiating ZODB backup...')
        zodb_handler = ZenDB(useDefault='zodb')
        self._zodb_backup_file_handler = open(os.path.join(self.tempDir, 'zodb.sql.gz'), 'wb')
        (self._zodb_mysqldump_process, self._zodb_backup_gzip_process) = zodb_handler.asynchronousDump(self._zodb_backup_file_handler)
        
        self._zodb_session_backup_file_handler = open(os.path.join(self.tempDir, 'zodb_session.sql.gz'), 'wb')
        (self._zodb_session_mysqldump_process, self._zodb_session_backup_gzip_process) = zodb_handler.asynchronousDump(self._zodb_session_backup_file_handler, no_data=True)
    
    def waitForZODBBackup(self):
        """
        Wait for the ZODB backup to finish (which was kicked off from the method startBackupZODB)
        """
        partBeginTime = time.time()
        self.log.info("Waiting for the ZODB backup to finish...")
        
        self._zodb_mysqldump_process.wait()
        self._zodb_backup_gzip_process.wait()
        self._zodb_backup_file_handler.close()
        
        self._zodb_session_mysqldump_process.wait()
        self._zodb_session_backup_gzip_process.wait()
        self._zodb_session_backup_file_handler.close()
        
        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Waited %s seconds for the ZODB backup to finish.", subtotalTime)
    
    def backupPerfData(self):
        """
        Back up the RRD files storing performance data.
        """
        perfDir = zenPath('perf')
        if not os.path.isdir(perfDir):
            self.log.warning('%s does not exist, skipping.', perfDir)
            return

        partBeginTime = time.time()

        self.log.info('Backing up performance data (RRDs).')
        tarFile = os.path.join(self.tempDir, 'perf.tar')
        #will change dir to ZENHOME so that tar dir structure is relative
        cmd = ['tar', 'chfC', tarFile, zenPath(), 'perf']
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            raise ZenBackupException("Performance Data backup failed.", True)

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of performance data completed in %s.",
                      subtotalTime )


    def packageStagingBackups(self):
        """
        Gather all of the other data into one nice, neat file for easy
        tracking. Returns the filename created.
        """
        self.log.info('Packaging backup file.')
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDefaultBackupFile()
        tempHead, tempTail = os.path.split(self.tempDir)
        tarFile = outfile
        if self.options.stdout:
            tarFile = '-'
        cmd = ['tar', 'czfC', tarFile, tempHead, tempTail]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            raise ZenBackupException("Backup packaging failed.", True)
        self.log.info('Backup written to %s', outfile)
        return outfile


    def cleanupTempDir(self):
        """
        Remove temporary files in staging directory.
        """
        self.log.info('Cleaning up staging directory %s', self.rootTempDir)
        cmd = ['rm', '-r', self.rootTempDir]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            raise ZenBackupException("Cleanup failed.")


    def makeBackup(self):
        '''
        Create a backup of the data and configuration for a Zenoss install.
        '''
        hasCriticalErrors = False
        messages = []
        backupBeginTime = time.time()

        # Create temp backup dir
        self.rootTempDir = self.getTempDir()
        self.tempDir = os.path.join(self.rootTempDir, BACKUP_DIR)
        self.log.debug("Use %s as a staging directory for the backup", self.tempDir)
        os.mkdir(self.tempDir, 0o750)

        if self.options.collector:
            self.options.noEventsDb = True
            self.options.noZopeDb = True
            self.options.noZepIndexes = True
            self.options.noZenPacks = True
        
        # Do a full backup of zep if noEventsDb is false, otherwise only back
        # up a small subset of tables to capture the event triggers.
        if not self.options.noEventsDb or not self.options.noZopeDb:
            try:
                self.backupZEP()
            except ZenBackupException as e:
                hasCriticalErrors = hasCriticalErrors or e.isCritical()
                messages.append(str(e))
        else:
            self.log.info('Skipping backup of the events database.')
        
        # Copy /etc to backup dir (except for sockets)
        self.log.info('Backing up config files.')
        etcTar = tarfile.open(os.path.join(self.tempDir, 'etc.tar'), 'w')
        etcTar.dereference = True
        etcTar.add(zenPath('etc'), 'etc')
        etcTar.close()
        self.log.info("Backup of config files completed.")
        
        if self.options.noZopeDb:
            self.log.info('Skipping backup of ZODB.')
        else:
            notify(PreBackupEvent(self))
            self.startBackupZODB()

        if self.options.noZenPacks:
            self.log.info('Skipping backup of ZenPack data.')
        else:
            partBeginTime = time.time()
            self.backupZenPacks()
            self.backupZenPackContents()
            partEndTime = time.time()
            subtotalTime = readable_time(partEndTime - partBeginTime)
            self.log.info("Backup of ZenPacks completed in %s.", subtotalTime)
        
        notify(PostBackupEvent(self))
        if not self.options.noZopeDb:
            self.waitForZODBBackup()

        if self.options.noPerfData:
            self.log.info('Skipping backup of performance data.')
        else:
            try:
                self.backupPerfData()
            except ZenBackupException as e:
                hasCriticalErrors = hasCriticalErrors or e.isCritical()
                messages.append(str(e))

        # tar, gzip and send to outfile
        try:
            outfile = self.packageStagingBackups()
        except ZenBackupException as e:
                hasCriticalErrors = hasCriticalErrors or e.isCritical()
                messages.append(str(e))

        try:
            self.cleanupTempDir()
        except ZenBackupException as e:
                hasCriticalErrors = hasCriticalErrors or e.isCritical()
                messages.append(str(e))
        
        if not hasCriticalErrors:
            backupEndTime = time.time()
            totalBackupTime = readable_time(backupEndTime - backupBeginTime)
            if len(messages) == 0:
                self.log.info('Backup completed successfully in %s.', totalBackupTime)
            else:
                self.log.info('Backup completed successfully in %s, but the following errors occurred:', totalBackupTime)
                for msg in messages:
                    self.log.error(msg)
            return 0
        else:
            for msg in messages:
                self.log.critical(msg)
            return -1
        
        # TODO: There's no way to tell if this initiated through the UI.
        # audit('Shell.Backup.Create', file=outfile)

if __name__ == '__main__':
    zb = ZenBackup(sys.argv)
    if zb.makeBackup():
        sys.exit(-1)
