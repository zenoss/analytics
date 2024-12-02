#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

'''
Send events on a command line via XML-RPC.

This command can be put on any machine with Python installed, and
does not need Zope or Zenoss.

Sending events from a XML file requires either:
 * called from Zenoss box that has $ZENHOME/Products/ZenEvents/XmlEvents.py
 * a copy of XmlEvents.py in the same directory as this file
'''

from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class ImportEventXML(ContentHandler):
    ignoredElements = set([
        'ZenossEvents', 'url', 'SourceComponent',
        'ReporterComponent', 'EventId',
        'clearid', 'eventClassMapping',
        'eventState', 'lastTime', 'firstTime', 'prodState',
        'EventSpecific', 'stateChange',
        ])
    evt = {}
    property = ''
    value = ''

    def __init__(self, serv, log=None):
        ContentHandler.__init__(self)
        self.sent = 0
        self.total = 0
        self.serv = serv
        self.log = log

    def startElement(self, name, attrs):
        self.value = ''
        if name == 'ZenossEvent':
            self.evt = {}
        elif name == 'property':
            self.property = attrs['name']

    def characters(self, content):
        self.value += content

    def endElement(self, name):
        name = str(name)
        value = str(self.value)
        if name in self.ignoredElements:
            return

        elif name == 'property' and value and value != '|':
                self.evt[self.property] = value

        elif name in ['Systems', 'DeviceGroups']:
                if value and value != '|':
                    self.evt[name] = value

        elif name in ['eventClassKey', 'eventKey']:
                if value:
                    self.evt[name] = value

        elif name == 'severity':
                self.evt[name] = int(value)

        elif name == 'ZenossEvent':
            self.total += 1
            try:
                self.serv.sendEvent(self.evt)
                self.sent += 1
            except Exception as ex:
                if self.log is not None:
                    self.log.error("Events XML import failed with %s -- data: %s",
                                   ex, self.evt)
                else:
                    print str(ex)
                    print self.evt

        elif value:
            self.evt[name] = value


def sendXMLEvents(serv, xmlfile, log=None):
    parser = make_parser()
    CH = ImportEventXML(serv, log=log)
    parser.setContentHandler(CH)
    # Raises exception if the file could not be read and parsed
    parser.parse(xmlfile)
    return CH.sent, CH.total


if __name__ == '__main__':
    # The following code assumes we are running from within a Zenoss box
    import logging
    log = logging.getLogger('zen.importEvents')
    from Products.ZenUtils.ZCmdBase import ZCmdBase

    class CmdLineImporter(ZCmdBase):
        def buildOptions(self):
            ZCmdBase.buildOptions(self)
            self.parser.add_option('-i', '--file',
             dest = "input_file",
             help = "Events.xml file to import")

    cmdBase = CmdLineImporter()
    cmdBase.parseOptions()
    serv = cmdBase.dmd.ZenEventManager
    sent, total = sendXMLEvents(serv, cmdBase.options.input_file, log)
    print "Sent %s of %s events" % (sent, total)

