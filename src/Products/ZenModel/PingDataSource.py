##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """PingDataSource.py

Defines datasource for zenping
"""

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
import Products.ZenModel.RRDDataSource as RRDDataSource
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD

PING_DATAPOINTS = (
    'rtt_avg',
    'rtt_min',
    'rtt_max',
    'rtt_losspct',
    'rtt_stddev',
)

class PingDataSource(RRDDataSource.RRDDataSource):
    
    PING = 'PING'
    
    sourcetypes = (PING,)
    sourcetype = PING

    timeout = 2
    eventClass = '/Status/Ping'
        
    cycleTime = 60
    sampleSize = 1
    attempts = 2

    _properties = RRDDataSource.RRDDataSource._properties + (
        {'id':'cycleTime', 'type':'int', 'mode':'w'},
        {'id':'sampleSize', 'type':'int', 'mode':'w'},
        {'id':'attempts', 'type':'int', 'mode':'w'},
        )
        
    security = ClassSecurityInfo()

    def __init__(self, id, title=None, buildRelations=True):
        RRDDataSource.RRDDataSource.__init__(self, id, title, buildRelations)

    def getDescription(self):
        if self.sourcetype == self.PING:
            return "Ping "
        return RRDDataSource.RRDDataSource.getDescription(self)

    def useZenCommand(self):
        return False

    security.declareProtected(ZEN_MANAGE_DMD, 'addDataPoints')
    def addDataPoints(self):
        for dp in PING_DATAPOINTS:
            if self.datapoints._getOb(dp, None) is None:
                self.manage_addRRDDataPoint(dp)

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        '''validation, etc'''
        if REQUEST:
            # ensure default datapoint didn't go away
            self.addDataPoints()
            # and eventClass
            if not REQUEST.form.get('eventClass', None):
                REQUEST.form['eventClass'] = self.__class__.eventClass
        return RRDDataSource.RRDDataSource.zmanage_editProperties(self, REQUEST)

InitializeClass(PingDataSource)
