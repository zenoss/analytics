#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
from optparse import OptionParser
from amqplib.client_0_8.connection import Connection
from contextlib import closing

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

import logging
LOG = logging.getLogger("zen.qverify")

def _addSetting(name, settings, globalSettings, default=None):
    setting = globalSettings.get(name, default)
    if setting is not None:
        settings[name] = setting

_ZEN_AMQP_SETTINGS =  {
   'amqphost': 'localhost',
   'amqpport': 5672,
   'amqpuser': 'zenoss',
   'amqppassword': 'zenoss',
   'amqpvhost': '/zenoss',
   'amqpusessl': False,
   'amqpadminport': 55672,
   'amqpadminusessl': False,
}

class ZenAmqp(object):

    def __init__(self):
        self._global_conf = getGlobalConfiguration()

    def _getSettings(self, admin, extraParams=None):
        sslkey = 'amqpadminusessl' if admin else 'amqpusessl'
        port = 'amqpadminport' if admin else 'amqpport'
        zenSettings = {}
        for setting, default in _ZEN_AMQP_SETTINGS.iteritems():
            _addSetting(setting, zenSettings, self._global_conf, default)
        if extraParams:
            zenSettings.update(extraParams)
        ssl = zenSettings.get(sslkey, False) in ('1', 'True', 'true', 1, True)
        settings = {
            'host': '%s:%s' % (zenSettings['amqphost'], zenSettings[port]),
            'userid': '%(amqpuser)s' % zenSettings,
            'password': '%(amqppassword)s' % zenSettings,
            'virtual_host': '%(amqpvhost)s' % zenSettings,
            'ssl': ssl,
        }
        # provide a method for overriding system supplied values
        if extraParams:
            for name, value in extraParams.iteritems():
                if name not in _ZEN_AMQP_SETTINGS:
                    settings[name] = value
        return settings

    def getAdminConnectionSettings(self, extraParams=None):
        return self._getSettings(admin=True, extraParams=extraParams)

    def getConnectionSettings(self, extraParams=None):
        return self._getSettings(admin=False, extraParams=extraParams)

    def getConnection(self):
        settings = self.getConnectionSettings()
        return Connection(**settings)

    def getVersion(self):
        with closing(self.getConnection()) as conn:
             return conn.server_properties.get('version')

class Main(object):
    def __init__(self, verbose=False):
        self._verbose = verbose
        LOG.debug("Getting global conf")
        self._global_conf = getGlobalConfiguration()

    def _get_setting(self, name):
        val = self._global_conf.get(name, None)
        if val is None:
            print >> sys.stderr, "global.conf setting %s must be set." % name
            sys.exit(1)
        return val

    def verify_settings(self):
        # verify all settings exist
        for setting in _ZEN_AMQP_SETTINGS:
            self._get_setting(setting)

    def verify(self, expected_version, check_settings):
        rc = 1
        conn = None
        if check_settings:
            self.verify_settings()
        try:
            conn = ZenAmqp().getConnection()
            server_version = conn.server_properties.get('version')
            if expected_version:
                e_ver = tuple(int(v) for v in expected_version.split('.'))
                s_ver = tuple(int(v) for v in server_version.split('.'))
                if s_ver < e_ver:
                    print >> sys.stderr, "Server version: %s < Expected version: %s" % (
                        server_version, expected_version)
                    rc = 2
                else:
                    if self._verbose:
                        print "Server version: %s" % server_version
                    rc = 0
            else:
                if self._verbose:
                    print "Server version: %s" % server_version
                rc = 0
        finally:
            if conn:
                conn.close()
        sys.exit(rc)

if __name__=="__main__":
    usage = "%prog VERSION_NUMBER?" 
    epilog = "Verifies connectivity with the amqp server configued in global.conf and " \
             "checks if server version is >= VERSION_NUMBER. Returns exit code 1 if " \
             "connection fails, 2 if server version < VERSION_NUMBER, and 0 if " \
             "connection is OK and server version >= VERSION_NUMBER."
    parser = OptionParser(usage=usage, epilog=epilog)
    parser.add_option("--verbose", "-v", default=False, action='store_true')
    parser.add_option("--disable-settings-check", default=False, action='store_true', dest='disable_settings_check')
    (options, args) = parser.parse_args()

    version = None
    if len(args) >= 1:
       version = args[0]

    main = Main(options.verbose) 
    main.verify( version, not options.disable_settings_check)
