##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""BasicDataSource

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.
"""

from Products.ZenModel import RRDDataSource
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD, ZEN_CHANGE_DEVICE
from AccessControl import ClassSecurityInfo, Permissions
from AccessControl.class_init import InitializeClass
from Products.ZenModel.Commandable import Commandable
from Products.ZenEvents.ZenEventClasses import Cmd_Fail
from Products.ZenUtils.Utils import executeStreamCommand, executeSshCommand, escapeSpecChars
from Products.ZenWidgets import messaging
from copy import copy
import cgi, time

snmptemplate = ("snmpwalk -c%(zSnmpCommunity)s "
                "-%(zSnmpVer)s %(manageIp)s %(oid)s")

def checkOid(oid):
    import string
    for c in string.whitespace:
        oid = oid.replace(c, '')
    oid = oid.strip('.')
    numbers = oid.split('.')
    map(int, numbers)
    if len(numbers) < 3:
        raise ValueError("OID too short")
    return oid


class SnmpCommand(object):
    '''
    Builds the command for SNMP.i  v3 has additional arguments
    while v1/v2 just use the string template.
    '''
    def __init__(self, snmpinfo):
        self.snmpinfo = snmpinfo
        self.command, self.display = self._getCommand()

    def _getCommand(self):
        command = snmptemplate % self.snmpinfo

        if self.snmpinfo['zSnmpVer'] != 'v3':
            return (command, command)

        # v3 always requires the username
        command += (" -u%(zSnmpSecurityName)s" % self.snmpinfo)
        display = command

        if self.snmpinfo['zSnmpPrivType'] and self.snmpinfo['zSnmpAuthType']:
            display += (" -l authPriv -a %(zSnmpAuthType)s " % self.snmpinfo) + "-A ${zSnmpAuthPassword} " + \
                ("-x %(zSnmpPrivType)s " % self.snmpinfo) + "-X ${zSnmpPrivPassword}"
            command += (" -l authPriv -a %(zSnmpAuthType)s -A %(zSnmpAuthPassword)s "
                "-x %(zSnmpPrivType)s -X %(zSnmpPrivPassword)s" % self.snmpinfo)
        elif self.snmpinfo['zSnmpAuthType']:
            display += (" -l authNoPriv -a %(zSnmpAuthType)s " % self.snmpinfo) + "-A ${zSnmpAuthPassword}"
            command += (" -l authNoPriv -a %(zSnmpAuthType)s -A %(zSnmpAuthPassword)s" % self.snmpinfo)
        else:
            display += " -l noAuthNoPriv"
            command += " -l noAuthNoPriv"

        return (command, display)


class BasicDataSource(RRDDataSource.SimpleRRDDataSource, Commandable):

    __pychecker__='no-override'

    sourcetypes = ('SNMP', 'COMMAND')

    sourcetype = 'SNMP'
    eventClass = Cmd_Fail
    oid = ''
    parser = "Auto"

    usessh = False

    _properties = RRDDataSource.RRDDataSource._properties + (
        {'id':'oid', 'type':'string', 'mode':'w'},
        {'id':'usessh', 'type':'boolean', 'mode':'w'},
        {'id':'parser', 'type':'string', 'mode':'w'},
        )

    _relations = RRDDataSource.RRDDataSource._relations + (
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
    {
        'immediate_view' : 'editBasicDataSource',
        'actions'        :
        (
            { 'id'            : 'edit'
            , 'name'          : 'Data Source'
            , 'action'        : 'editBasicDataSource'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    def addDataPoints(self):
        """
        Overrides method defined in SimpleRRDDataSource. Only sync the
        datapoint with the datasource if the datasource type is SNMP.
        """
        if self.sourcetype == 'SNMP':
            RRDDataSource.SimpleRRDDataSource.addDataPoints(self)

    def getDescription(self):
        if self.sourcetype == "SNMP":
            return self.oid
        if self.sourcetype == "COMMAND":
            if self.usessh:
                return self.commandTemplate + " over SSH"
            else:
                return self.commandTemplate
        return RRDDataSource.RRDDataSource.getDescription(self)

    def useZenCommand(self):
        if self.sourcetype == 'COMMAND':
            return True
        return False

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        'add some validation'
        if REQUEST:
            oid = REQUEST.get('oid', '')
            if oid:
                try:
                    REQUEST.form['oid'] = checkOid(oid)
                except ValueError:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Invalid OID',
                        "%s is an invalid OID." % oid,
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)

        return RRDDataSource.SimpleRRDDataSource.zmanage_editProperties(
                                                                self, REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'manage_testDataSource')
    def manage_testDataSource(self, testDevice, REQUEST):
        ''' Test the datasource by executing the command and outputting the
        non-quiet results.
        '''
        # set up the output method for our test
        out = REQUEST.RESPONSE
        def write(lines):
            ''' Output (maybe partial) result text.
            '''
            # Looks like firefox renders progressive output more smoothly
            # if each line is stuck into a table row.
            startLine = '<tr><td class="tablevalues">'
            endLine = '</td></tr>\n'
            if out:
                if not isinstance(lines, list):
                    lines = [lines]
                for l in lines:
                    if not isinstance(l, str):
                        l = str(l)
                    l = l.strip()
                    l = cgi.escape(l)
                    l = l.replace('\n', endLine + startLine)
                    out.write(startLine + l + endLine)

        # use our input and output to call the testDataSource Method
        errorLog = messaging.IMessageSender(self).sendToBrowser
        return self.testDataSourceAgainstDevice(testDevice,
                                                REQUEST,
                                                write,
                                                errorLog)

    def parsers(self):
        from Products.DataCollector.Plugins import loadParserPlugins
        return sorted(p.modPath for p in loadParserPlugins(self.getDmd()))


InitializeClass(BasicDataSource)
