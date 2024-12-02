##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""DefGraphPoint

Handles GraphPoints that define an rrd DEF
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass


def manage_addDefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = DefGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class DefGraphPoint(GraphPoint):

    meta_type = 'DefGraphPoint'
    
    rrdFile = ''
    dsName = 'ds0'
    step = ''
    start = ''
    end = ''
    cFunc = 'AVERAGE'
    rFunc = ''
    
    _properties = GraphPoint._properties + (
        {'id':'rrdFile', 'type':'string', 'mode':'w'},
        {'id':'dsName', 'type':'string', 'mode':'w'},
        {'id':'step', 'type':'string', 'mode':'w'},
        {'id':'start', 'type':'string', 'mode':'w'},
        {'id':'end', 'type':'string', 'mode':'w'},
        {'id':'cFunc', 'type':'string', 'mode':'w'},
        {'id':'rFunc', 'type':'string', 'mode':'w'},        
        )
    

    def getDescription(self):
        return '%s %s' % (self.rrdFile, self.dsName)


    def getType(self):
        return 'DEF'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                            multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        if not (self.rrdFile and self.dsName and self.cFunc):
            return cmds
        
        rrdFile = self.talesEval(self.rrdFile, context, rrdDir=rrdDir)    
            
        dest = self.getDsName(self.id, multiid, prefix)
        gopt = 'DEF:%s=%s:%s:%s' % (
                    dest,
                    rrdFile,
                    self.dsName,
                    self.cFunc)
        if self.step:
            gopt += ':step=%s' % self.step
        if self.start:
            start = self.talesEval(self.start, context)
            gopt += ':start=%s' % start.replace(':', '\:')
        if self.end:
            end = self.talesEval(self.end, context)
            gopt += ':end=%s' % end.replace(':', '\:')
        if self.rFunc:
            gopt += ':reduce=%s' % self.rFunc        
        return cmds + [gopt]


InitializeClass(DefGraphPoint)
