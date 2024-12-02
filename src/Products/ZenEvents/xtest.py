#! /usr/bin/env python 
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''xtest.py

Sends test events to zenoss via xml-rpc.
Events can be specified on the command line or read from a file.
'''

from Products.ZenUtils.CmdBase import CmdBase
import xmlrpclib
import time
import sys
from Products.ZenEvents.ZenEventClasses import Status_Perf

# Input files must be in python format and contain a list named 'events'
# that contains one dictionary per test event.
# Each of these dictionaries should have values for device, summary, component
# and severity.
#Example:
#
#events = [
#    {
#        'device': 'Device1a',
#        'summary': 'This is the summary.',
#        'component': 'Some component',
#        'severity': 4,
#    },
#    {
#        'device': 'Device2a',
#        'summary': 'This is the summary.',
#        'component': 'Some component',
#        'severity': 4,
#    },
#]


class XTest(CmdBase):

    # Sample event and corresponding clear event used by several methods.
    sampleEvent = dict(device='Sample device',
                        summary='Test event at %s' % time.time(),
                        eventClass=Status_Perf,
                        severity=4,
                        component='Sample component')
    sampleClear = sampleEvent.copy()
    sampleClear.update(dict(
                        severity=0,
                        summary='Clear event'))


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)
        self.proxy = None
        

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)
        self.parser.add_option('--file',
                    dest="filepath",default=None,
                    help="file containing event details")
        self.parser.add_option('--sample',
                    dest='dosample', default=False,
                    action='store_true',
                    help='Send sample event and clear event')
        self.parser.add_option('-d', '--device',
                    dest="device",default='',
                    help="device to use for event")
        self.parser.add_option('-s', '--summary',
                    dest="summary",default='',
                    help="summary to use for event")
        self.parser.add_option('-c', '--component',
                    dest="component",default='',
                    help="component to use for event")
        self.parser.add_option('-y', '--severity',
                    dest="severity",default=4,
                    type='int',
                    help="severity to use for event")
        self.parser.add_option('--rpchost',
                    dest="rpchost",default='localhost',
                    help="host for xml-rpc request")
        self.parser.add_option('--rpcport',
                    dest="rpcport",default='8081',
                    help="port for xml-rpc request")
                    

    def parseEventsFile(self, filepath=None):
        ''' Not much actual parsing going on here, just importing
        the given file. 
        '''
        if not filepath:
            filepath = self.options.filepath
        args = {}
        execfile(filepath, {}, args)
        if 'events' in args:
            events = args['events']
        else:
            events = []
            sys.stderr.write('%s has no value for events\n' % filepath)
        return events
    

    def getXmlRpcProxy(self):
        ''' Returns xmlrpc proxy, creating on if the instance doesn't
        already have one.
        '''
        if not self.proxy:
            self.proxy = xmlrpclib.ServerProxy(
                'http://%s:%s/' % (self.options.rpchost, self.options.rpcport),
                #verbose=1,
                encoding='iso-8859-1')
        return self.proxy


    def sendEvents(self, events):
        ''' events is a list of dictionaries with details of events to send.
        This sends those events via the xmlrpc proxy.
        '''
        proxy = self.getXmlRpcProxy()
        proxy.sendEvents(events)


    def sendSampleEvents(self, repeat=1):
        ''' Sends the sample event and corresponding clear event.
        Repeats this as many times as specified by repeat.
        '''
        for i in range(repeat):
            self.sendEvents([self.sampleEvent, self.sampleClear])

            
    def sendSampleWithDelayedClear(self, repeat=1, delay=30):
        ''' Sends sample event then after a delay sends the clear event,
        repeating as specified.
        '''
        self.sendEvents([self.sampleEvent])
        time.sleep(30)
        self.sendEvents([self.sampleClear])

        
    def sendEventsFromFile(self, filepath=None):
        ''' Parse the given file (or the file specified at init) and
        send the files.
        '''
        events = self.parseEventsFile(filepath=filepath)
        self.sendEvents(events)


def main():
    "performance test"
    xt = XTest()
    xt.sendSampleEvents(repeat=100)

def coverage():
    xt = XTest()
    xt.sendSampleEvents()
    xt.sendEvents([xt.sampleEvent])
    proxy = xt.getXmlRpcProxy()
    issues = proxy.getDevicePingIssues()
    for i in issues:
        print i

def simple():
    xt = XTest()
    xt.sendSmapleWithDelayedClear()

if __name__ == '__main__':
    xt = XTest()
    if xt.options.dosample:
        xt.sendSampleEvents()
    elif xt.options.filepath:
        xt.sendEventsFromFile()
    elif xt.options.device:
        event = dict(device=xt.options.device,
                        summary=xt.options.summary, 
                        component=xt.options.component, 
                        severity=xt.options.severity)
        xt.sendEvents([event])
    else:
        xt.parser.print_help()
