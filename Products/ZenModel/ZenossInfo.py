##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os
import os.path
import sys
import re
from functools import wraps
from urllib import unquote
import subprocess
from subprocess import Popen, PIPE
from xml.dom.minidom import parse
import shutil
import traceback
import logging

from AccessControl.class_init import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelItem import ZenModelItem
from Products.ZenCallHome.transport.methods.versioncheck import version_check
from Products.ZenUtils.mysql import MySQLdb
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.Version import (Version, VersionNotSupported,
                                       getVersionTupleFromString)
from Products.ZenUtils.path import binPath, isZenBinFile, zenPath
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGE_DMD, ZEN_MANAGE_GLOBAL_SETTINGS, ZEN_MANAGE_USERS,
    ZEN_VIEW_USERS, ZEN_MANAGE_GLOBAL_COMMANDS, ZEN_MANAGE_ZENPACKS,
    ZEN_VIEW_SOFTWARE_VERSIONS, ZEN_MANAGE_EVENT_CONFIG, ZEN_MANAGE_UI_SETTINGS
)

log = logging.getLogger("zen.ZenossInfo")


def versionmeta(name, href, optional=False):
    """
    Used as a decorator, this function attaches attributes 'name' and
    'href' to the methods providing Version objects.  If optional is True,
    return None rather than raising an exception if version data cannot be
    retrieved.
    """
    def _versionmeta(f):
        f.name = name
        f.href = href
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception:
                if optional:
                    return None
                else:
                    raise
        return wrapper
    return _versionmeta


def manage_addZenossInfo(context, id='About', REQUEST=None):
    """
    Provide an instance of ZenossInfo for the portal.
    """
    about = ZenossInfo(id)
    context._setObject(id, about)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url_path() + '/manage_main')


class ZenossInfo(ZenModelItem, SimpleItem):

    portal_type = meta_type = 'ZenossInfo'

    security = ClassSecurityInfo()

    _properties = (
        {'id': 'id', 'type': 'string'},
        {'id': 'title', 'type': 'string'},
    )

    factory_type_information = (
        {
            'immediate_view' : 'zenossInfo',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../dmd/editSettings'
                , 'permissions'   : ( ZEN_MANAGE_GLOBAL_SETTINGS, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dmd/dataRootManage'
                , 'permissions'   : (ZEN_MANAGE_GLOBAL_COMMANDS,)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : '../dmd/ZenUsers/manageUserFolder'
                , 'permissions'   : (ZEN_VIEW_USERS, ZEN_MANAGE_USERS, )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : '../dmd/ZenPackManager/viewZenPacks'
                , 'permissions'   : (ZEN_MANAGE_ZENPACKS, )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../dmd/editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : 'zenossVersions'
                , 'permissions'   : (ZEN_VIEW_SOFTWARE_VERSIONS,)
                },
                { 'id'            : 'eventConfig'
                , 'name'          : 'Events'
                , 'action'        : 'eventConfig'
                , 'permissions'   : (ZEN_MANAGE_EVENT_CONFIG,)
                },
                { 'id'            : 'userInterfaceConfig'
                , 'name'          : 'User Interface'
                , 'action'        : '../dmd/userInterfaceConfig'
                , 'permissions'   : (ZEN_MANAGE_UI_SETTINGS,)
                },
           )
          },
        )


    def titleOrId(self):
        return self.title or self.id

    def breadCrumbs(self, target='dmd'):
        return []

    @versionmeta("Zenoss", "http://www.zenoss.com")
    def getZenossVersion(self):
        from Products.ZenModel.ZVersion import VERSION
        return Version.parse("Zenoss %s" % VERSION)
    security.declarePublic('getZenossVersion')

    @versionmeta("Zenoss", "http://www.zenoss.com")
    def getZenossVersionAndBuild(self):
        from Products.ZenModel.ZVersion import VERSION, BUILD_NUMBER
        return Version.parse("Zenoss %s %s" % (VERSION, BUILD_NUMBER))
    security.declarePublic('getZenossVersionAndBuild')

    def getZenossVersionShort(self):
        return self.getZenossVersion().short()
    security.declarePublic('getZenossVersionShort')

    @versionmeta("Control Center", "http://controlcenter.io/")
    def getControlCenterVersion(self):
        """
        This is intended to run from within a container.
        """
        version = Version('ControlCenter')
        if os.path.exists('/serviced/serviced'):
            try:
                # Note the port given below is not used when getting the version, but overrides the
                # SERVICED_UI_PORT env variable that can cause it to fail cli parameter validation.
                output = subprocess.check_output([
                    '/serviced/serviced', '--uiport', ':1', 'version'
                ], stderr=subprocess.STDOUT)
                for line in output.split('\n'):
                    splitLine = line.split()
                    if splitLine[0] == 'Version:':
                        version = Version.parse('ControlCenter {}'.format(splitLine[1]))
                        break
            except subprocess.CalledProcessError as e:
                pass

        return version

    @versionmeta("OS", "http://www.tldp.org")
    def getOSVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getOSVersion())
            v.full()
        """
        if os.name == 'posix':
            sysname, nodename, version, build, arch = os.uname()
            name = "%s (%s)" % (sysname, arch)
            major, minor, micro = getVersionTupleFromString(version)
            comment = ' '.join(os.uname())
        elif os.name == 'nt':
            from win32api import GetVersionEx
            major, minor, micro, platformID, additional = GetVersionEx()
            name = 'Windows %s (%s)' % (os.name.upper(), additional)
            comment = ''
        else:
            raise VersionNotSupported
        return Version(name, major, minor, micro, 0, comment)

    @versionmeta("Python", "http://www.python.org")
    def getPythonVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getPythonVersion())
            v.full()
        """
        name = 'Python'
        major, minor, micro, releaselevel, serial = sys.version_info
        return Version(name, major, minor, micro)

    @versionmeta("Database", "http://www.mysql.com")
    def getMySQLVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getMySQLVersion())
            v.full()
        """
        cfg = getGlobalConfiguration()
        params = {
                'host': cfg.get("zodb-host", "localhost"),
                'port': int(cfg.get("zodb-port", 3306)),
                'user': cfg.get("zodb-user", "zenoss"),
                'passwd': cfg.get("zodb-password", "zenoss"),
            }
        if "zodb-socket" in cfg:
            params["unix_socket"] = cfg["zodb-socket"]
        db = None
        name = "MySQL"
        try:
            db = MySQLdb.connect(**params)
            db.query("select version()")
            data = db.use_result().fetch_row()
            if data:
                regex = re.compile("([0-9]+)\.([0-9]+)\.([0-9]+)(.*)")
                versionstr = data[0][0]
                match = regex.match(versionstr)
                if match:
                    major, minor, micro, info = match.groups()
                    return Version(
                            name,
                            int(major), int(minor), int(micro), 0,
                            versionstr
                        )
            raise RuntimeError("Unable to determine %s version" % (name,))
        finally:
            if db:
                db.close()

    @versionmeta("Twisted", "http:///twistedmatrix.com/trac")
    def getTwistedVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getTwistedVersion())
            v.full()
        """
        from twisted import version as v

        return Version('Twisted', v.major, v.minor, v.micro)

    @versionmeta("Zope", "http://www.zope.org")
    def getZopeVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getZopeVersion())
            v.full()
        """
        from App import version_txt as version

        name = 'Zope'
        major, minor, micro, status, release = version.getZopeVersion()
        return Version(name, major, minor, micro)

    @versionmeta("NetSnmp", "http://net-snmp.sourceforge.net", optional=True)
    def getNetSnmpVersion(self):
        from pynetsnmp.netsnmp import lib
        return Version.parse('NetSnmp %s ' % lib.netsnmp_get_version())

    @versionmeta("PyNetSnmp", "http://www.zenoss.com", optional=True)
    def getPyNetSnmpVersion(self):
        from pynetsnmp.version import VERSION
        return Version.parse('PyNetSnmp %s ' % VERSION)

    @versionmeta("WMI", "http://www.zenoss.com", optional=True)
    def getWmiVersion(self):
        from pysamba.version import VERSION
        return Version.parse('Wmi %s ' % VERSION)

    @versionmeta("RabbitMQ", "http://www.rabbitmq.com/")
    def getRabbitMQVersion(self):
        from Products.ZenUtils.qverify import ZenAmqp
        return Version.parse("RabbitMQ %s" % ZenAmqp().getVersion())

    def getAllVersions(self):
        """
        Return a list of version numbers for currently tracked component
        software.
        """
        versionfuncs = [
                self.getZenossVersionAndBuild,
                self.getOSVersion,
                self.getZopeVersion,
                self.getPythonVersion,
                self.getMySQLVersion,
                self.getTwistedVersion,
                self.getRabbitMQVersion,
                self.getNetSnmpVersion,
                self.getPyNetSnmpVersion,
                self.getWmiVersion,
                self.getControlCenterVersion
            ]
        versions = []
        for func in versionfuncs:
            try:
                version = func()
                # Skip this component if the return value is None
                if version is None:
                    continue
                data = version.full()
            except Exception:
                log.exception(
                    "Failed to retrieve '%s' version data", func.name
                )
                data = None
            versions.append({
                'header': func.name, 'data': data, 'href': func.href
            })
        return versions
    security.declareProtected('View', 'getAllVersions')

    def getAllUptimes(self):
        """
        Return a list of daemons with their uptimes.
        """
        app = self.getPhysicalRoot()
        uptimes = []
        zope = {
            'header': 'Zope',
            'data': app.Control_Panel.process_time(),
        }
        uptimes.append(zope)
        return uptimes
    security.declareProtected('View', 'getAllUptimes')

    daemon_tooltips = {
      "zeoctl": "Zope Enterprise Objects server (shares database between Zope instances)",
      "zopectl": "The Zope open source web application server",
      "zenhub": "Broker between the data layer and the collection daemons",
      "zenping": "ICMP ping status monitoring",
      "zensyslog": "Collection of and classification of syslog events",
      "zenstatus": "Active TCP connection testing of remote daemons",
      "zenactiond": "Receives signals from processed events to execute notifications.",
      "zentrap": "Receives SNMP traps and turns them into events",
      "zenmodeler": "Configuration collection and configuration",
      "zenperfsnmp": "High performance asynchronous SNMP performance collection",
      "zencommand": "Runs plug-ins on the local box or on remote boxes through SSH",
      "zenprocess": "Process monitoring using SNMP host resources MIB",
      "zendisc": "Discover the network topology to find active IPs and devices",
      "zenrrdcached": "Controls the write cache for performance data",
      "zenmail": "Listen for e-mail and convert messages to Zenoss events",
      "zenpop3": "Connect via pop3 to an e-mail server and convert messages to Zenoss events",
    }

    def getZenossDaemonStates(self):
        """
        Return a data structures representing the states of the supported
        Zenoss daemons.
        """
        states = []
        activeButtons = {'button1': 'Restart', 'button2': 'Stop', 'button2state': True}
        inactiveButtons = {'button1': 'Start', 'button2': 'Stop', 'button2state': False}
        alwaysOnButtons = {'button1': 'Restart', 'button2': 'Stop', 'button2state': False}

        for daemon in self._getDaemonList():
            pid = self._getDaemonPID(daemon)
            if pid:
                if daemon == 'zopectl' or daemon == 'zenwebserver':
                    buttons = alwaysOnButtons
                else:
                    buttons = activeButtons
                msg = 'Up'
                color = '#0F0'
            else:
                buttons = inactiveButtons
                msg = 'Down'
                color = '#F00'

            if daemon in self.daemon_tooltips:
                tooltip = self.daemon_tooltips[daemon]
            else:
                tooltip = ''

            states.append({
                'name': daemon,
                'pid': pid,
                'msg': msg,
                'tooltip': tooltip,
                'color': color,
                'buttons': buttons})

        return states

    def _pidRunning(self, pid):
        try:
            os.kill(pid, 0)
            return pid
        except OSError as ex:
            import errno
            errnum, msg = ex.args
            if errnum == errno.EPERM:
                return pid

    def _getDaemonPID(self, name):
        """
        For a given daemon name, return its PID from a .pid file.
        """
        if name == 'zenwebserver':
            name = 'nginx'
        elif name == 'zopectl':
            name = 'Z2'
        elif name == 'zeoctl':
            name = 'ZEO'
        elif '_' in name:
            collector, daemon = name.split('_', 1)
            name = '%s-%s' % (daemon, collector)
        else:
            name = "%s-localhost" % name
        pidFile = zenPath('var', '%s.pid' % name)
        if os.path.exists(pidFile):
            pid = open(pidFile).read()
            try:
                pid = int(pid)
            except ValueError:
                return None
            return self._pidRunning(int(pid))
        else:
            pid = None
        return pid

    def _getDaemonList(self):
        """
        Get the list of supported Zenoss daemons.
        """
        masterScript = binPath('zenoss')
        daemons = []
        for line in os.popen("%s list" % masterScript).readlines():
            if 'zenrrdcache' not in line:
                daemons.append(line.strip())
        return daemons

    def getZenossDaemonConfigs(self):
        """
        Return a data structures representing the config infor for the
        supported Zenoss daemons.
        """
        return [ dict(name=x) for x in self._getDaemonList() ]

    def _readLogFile(self, filename, maxBytes):
        fh = open(filename)
        try:
            size = os.path.getsize(filename)
            if size > maxBytes:
                fh.seek(-maxBytes, 2)
                # the first line could be a partial line, so skip it
                fh.readline()
            return fh.read()
        finally:
            fh.close()

    def isValidDaemon(self, daemon):
        # overriden by distributed collector -- see DistributedServer.py
        return isZenBinFile(daemon) or daemon == 'event'

    def getDaemonName(self, daemon):
        # overridden by distributed collector -- see DistributedServer.py
        return daemon

    def _getLogPath(self, daemon):
        """
        Returns the path the log file for the daemon this is monkey-patched
        in the distributed collector zenpack to support the localhost
        subdirectory.
        """
        if daemon != 'event' and not self.isValidDaemon(daemon):
            raise ValueError("%r is not a valid daemon name" % daemon)
        return zenPath('log', "%s.log" % daemon)

    def getLogData(self, daemon, kb=500):
        """
        Get the last kb kilobytes of a daemon's log file contents.
        """
        if not self.isValidDaemon(daemon):
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error',
                '%s is not a valid daemon name' % daemon,
                priority=messaging.WARNING
            )
            return ' '

        maxBytes = 1024 * int(kb)
        if daemon in ('zopectl', 'zenwebserver'):
            daemon = 'event'
        elif daemon == 'zeoctl':
            daemon = 'zeo'
        if daemon in ('zopectl', 'zenwebserver'):
            daemon = 'event'
        elif daemon == 'zeoctl':
            daemon = 'zeo'
        if daemon != 'event' and self.getDaemonName(daemon) not in self._getDaemonList():
            return ''
        filename = self._getLogPath(daemon)
        # if there is no data read, we don't want to return something that can
        # be interptreted as "None", so we make the default a single white
        # space
        data = ' '
        try:
            data = self._readLogFile(filename, maxBytes) or ' '
        except Exception as ex:
            data = "Error reading %s log file '%s':\n%s" % (
                    daemon, filename, str(ex))
        return data

    def _getConfigFilename(self, daemon):
        if daemon in ('zopectl', 'zenwebserver'):
            daemon = 'zope'
        elif daemon == 'zeoctl':
            daemon = 'zeo'
        return zenPath('etc', "%s.conf" % daemon)

    def _readConfigFile(self, filename):
        fh = open(filename)
        try:
            return fh.read()
        finally:
            fh.close()

    def getConfigData(self, daemon):
        """
        Return the contents of the daemon's config file.
        """
        if daemon not in self._getDaemonList():
            return 'The daemon name is invalid.'

        filename = self._getConfigFilename(daemon)
        # if there is no data read, we don't want to return something that can
        # be interptreted as "None", so we make the default a single white
        # space
        data = ' '
        try:
            data = self._readConfigFile(filename) or  ' '
        except IOError:
            data = 'Unable to read config file'
        return data

    def manage_saveConfigData(self, REQUEST):
        """
        Save config data from REQUEST to the daemon's config file.
        """
        daemon = REQUEST.form.get('daemon')
        if not self.isValidDaemon(daemon):
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error',
                'The daemon name %r is invalid' % daemon,
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST, redirect=True)

        filename = self._getConfigFilename(daemon)
        try:
            fh = open(filename, 'w+')
            data = REQUEST.form.get('data')
            fh.write(data)
            audit('UI.Daemon.EditConfig', daemon)
        finally:
            fh.close()
        return self.callZenScreen(REQUEST, redirect=True)

    def parseconfig(self, filename=""):
        """
        From the given configuration file construct a configuration object
        """
        configs = {}

        config_file = open(filename)
        try:
            for line in config_file:
                line = line.strip()
                if line.startswith('#'): continue
                if line == '': continue

                try:
                    key, value = line.split(None, 1)
                except ValueError:
                    # Ignore errors
                    continue
                configs[key] = value
        finally:
            config_file.close()

        return configs

    def show_daemon_xml_configs(self, daemon, REQUEST=None ):
        """
        Display the daemon configuration options in an XML format.
        Merges the defaults with options in the config file.
        """
        # Sanity check
        if not daemon or daemon == '':
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error',
                'Called without a daemon name',
                priority=messaging.WARNING
            )
            return []

        if daemon in [ 'zeoctl', 'zopectl', 'zeneventserver' ]:
            return []

        # sanitize the input
        if daemon not in self._getDaemonList():
            return []
        if not self.isValidDaemon(daemon):
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error',
                '%s is not a valid daemon name' % daemon,
                priority=messaging.WARNING
            )
            return []

        xml_default_name = zenPath( "etc", daemon + ".xml" )
        try:
            # Always recreate the defaults file in order to avoid caching issues
            log.debug("Creating XML config file for %s", daemon)
            make_xml = ' '.join([binPath(daemon), "genxmlconfigs", ">", xml_default_name])
            proc = Popen(make_xml, shell=True, stdout=PIPE, stderr=PIPE)
            output, errors = proc.communicate()
            proc.wait()
            if proc.returncode != 0:
                log.error(errors)
                messaging.IMessageSender(self).sendToBrowser(
                    'Internal Error', errors,
                    priority=messaging.CRITICAL
                )
                return [["Output", output, errors, make_xml, "string"]]
        except Exception as ex:
            msg = "Unable to execute '%s'\noutput='%s'\nerrors='%s'\nex=%s" % (
                        make_xml, output, errors, ex)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["Error in command", output, errors, make_xml, "string"]]

        try:
            xml_defaults = parse( xml_default_name )
        except Exception:
            info = traceback.format_exc()
            msg = "Unable to parse XML file %s because %s" % (
                xml_default_name, info)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["Error parsing XML file", xml_default_name, "XML", info, "string"]]

        configfile = self._getConfigFilename(daemon)
        try:
            # Grab the current configs
            current_configs = self.parseconfig( configfile )
        except Exception:
            info = traceback.format_exc()
            msg = "Unable to obtain current configuration from %s because %s" % (
                       configfile, info)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["Configuration file issue", configfile, configfile, info, "string"]]

        all_options = {}
        ignore_options = ['configfile', 'cycle', 'daemon', 'weblog']
        try:
            for option in xml_defaults.getElementsByTagName('option'):
                id = option.attributes['id'].nodeValue
                if id in ignore_options:
                    continue
                try:
                    help = unquote(option.attributes['help'].nodeValue)
                except Exception:
                    help = ''

                try:
                    default = unquote(option.attributes['default'].nodeValue)
                except Exception:
                    default = ''
                if default == '[]':  # Attempt at a list argument -- ignore
                    continue

                all_options[id] = [
                    id,
                    current_configs.get(id, default),
                    default,
                    help.replace("%default", default),
                    option.attributes['type'].nodeValue,
                ]
        except Exception:
            info = traceback.format_exc()
            msg = "Unable to merge XML defaults with config file" \
                      " %s because %s" % (configfile, info)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["XML file issue", daemon, xml_default_name, info, "string"]]

        return [all_options[name] for name in sorted(all_options.keys())]

    def save_daemon_configs( self, REQUEST=None, **kwargs ):
        """
        Save the updated daemon configuration to disk.
        """
        if not REQUEST:
            return
        elif not hasattr(REQUEST, 'form'):
            return

        # Sanity check
        formdata = REQUEST.form
        ignore_names = ['save_daemon_configs', 'zenScreenName', 'daemon_name']

        daemon = formdata.get('daemon_name', '')
        if not daemon or daemon in ['zeoctl', 'zopectl']:
            return
        for item in ignore_names:
            del formdata[item]

        if not self.isValidDaemon(daemon):
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', "%r is not a valid daemon name" % daemon,
                priority=messaging.CRITICAL
            )
            return

        if not formdata: # If empty, don't overwrite -- assume an error
            msg = "Received empty form data for %s config -- ignoring" % (
                      daemon)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return

        configfile = self._getConfigFilename(daemon)
        config_file_pre = configfile + ".pre"
        try:
            config = open( config_file_pre, 'w' )
            config.write("# Config file written out from GUI\n")
            for key, value in formdata.items():
                if value == '':
                    continue
                config.write('%s %s\n' % (key, value))
            config.close()
        except Exception as ex:
            msg = "Couldn't write to %s because %s" % (config_file_pre, ex)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            config.close()
            try:
                os.unlink(config_file_pre)
            except Exception:
                pass
            return

        # If we got here things succeeded
        audit('UI.Daemon.EditConfig', daemon)

        config_file_save = configfile + ".save"
        try:
            shutil.copy(configfile, config_file_save)
        except Exception:
            log.error("Unable to make backup copy of %s", configfile)
            # Don't bother telling the user
        try:
            shutil.move(config_file_pre, configfile)
        except Exception:
            msg = "Unable to save contents to %s" % configfile
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )

    def manage_daemonAction(self, REQUEST):
        """
        Start, stop, or restart Zenoss daemons from a web interface.
        """
        legalValues = ['start', 'restart', 'stop']
        action = (REQUEST.form.get('action') or '').lower()
        if action not in legalValues:
            return self.callZenScreen(REQUEST)
        daemonName = REQUEST.form.get('daemon')
        if not self.isValidDaemon(daemonName):
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', "%r is not a valid daemon name" % daemonName,
                priority=messaging.CRITICAL
            )
            return self.callZenScreen(REQUEST)
        if self.doDaemonAction(daemonName, action):
            audit(['UI.Daemon', action], daemonName)
        return self.callZenScreen(REQUEST)
    security.declareProtected(ZEN_MANAGE_DMD, 'manage_daemonAction')

    def doDaemonAction(self, daemonName, action):
        """
        Do the given action (start, stop, restart) or the given daemon.
        Block until the action is completed.
        Returns False if an error was encountered, otherwise returns the action taken.
        """
        import time
        import subprocess
        daemonPath = binPath(daemonName)
        if not self.isValidDaemon(daemonName):
            return
        log.info('Telling %s to %s', daemonName, action)
        proc = subprocess.Popen([daemonPath, action], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
        output, _ = proc.communicate()
        code = proc.wait()
        if code:
            log.info('Error from %s: %s (%s)', daemonName, output, code)
        if action in ('stop', 'restart'):
            time.sleep(2)
        return False if code else action
    security.declareProtected(ZEN_MANAGE_DMD, 'doDaemonAction')

    def manage_checkVersion(self, optInOut=False, optInOutMetrics=False, REQUEST=None):
        "Check for Zenoss updates on the Zenoss website"
        self.dmd.versionCheckOptIn = optInOut
        self.dmd.reportMetricsOptIn = optInOutMetrics
        # There is a hidden field for manage_checkVersions in the form so that
        # the javascript submit() calls will end up calling this method.
        # That means that when user hits the Check Now button we will receive
        # 2 values for that field.  (button is that same field name.)
        # We want to initiate only when the button is pressed.
        #if self.dmd.versionCheckOptIn \
        #  and REQUEST \
        if REQUEST and isinstance(REQUEST.form['manage_checkVersion'], list):
            version_check(self.dmd)
        return self.callZenScreen(REQUEST)
    security.declareProtected(ZEN_MANAGE_DMD, 'manage_checkVersion')

    def lastVersionCheckedString(self):
        if not self.dmd.lastVersionCheck:
            return "Never"
        return self.convertToUsersTimeZone(self.dmd.lastVersionCheck)

    def versionBehind(self):
        if not self.dmd.availableVersion:
            return False
        if Version.parse('Zenoss ' + self.dmd.availableVersion) > self.getZenossVersion():
            return True
        return False

InitializeClass(ZenossInfo)
