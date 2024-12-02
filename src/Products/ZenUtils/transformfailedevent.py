#! /usr/bin/env python

import pickle
import logging
log = logging.getLogger('zen.replayTransform')


from zenoss.protocols.protobufs.zep_pb2 import Event

from Products.ZenEvents.Event import Event
from Products.ZenUtils.ZCmdBase import ZCmdBase
zodb = ZCmdBase(noopts=True)

class UnPickledEvent(ZCmdBase):

    def sendToRawEventQueue(self):
        if not self.options.eventFile:
            self.parser.error('Missing file argument!')
            return 0
        filename = self.options.eventFile
        try:
            with open(filename) as f:
                evt = pickle.load(f)               
                event = Event()
                event.updateFromDict(evt)
                zem = zodb.dmd.ZenEventManager
                zem.sendEvent(event)  
        except IOError as ex:
            log.error("Unable to process file %s: %s", filename, ex)
            return 0

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-i', '-f', '--file',
                    dest='eventFile',
                    help='Name of the file to replay')
        self.parser.set_defaults(logseverity=logging.DEBUG)


if __name__ == "__main__":
    unpickled = UnPickledEvent()
    unpickled.sendToRawEventQueue()
