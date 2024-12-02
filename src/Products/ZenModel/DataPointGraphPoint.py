##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""DPGraphPoint

Handles GraphPoints that refer to RRDDataPoints
"""

import os
import os.path
from ComplexGraphPoint import ComplexGraphPoint
from AccessControl.class_init import InitializeClass
from Products.ZenUtils.deprecated import deprecated

@deprecated
def manage_addDataPointGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = DataPointGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class DataPointGraphPoint(ComplexGraphPoint):
    '''
    '''
    meta_type = 'DataPointGraphPoint'
    
    # limit:   Maximum permitted value.  Values in excess of this are NaNed.
    #          Not used if negative
    limit = -1

    # rpn:     Reverse Polish Notation -- applied to the value for this graph point
    #          See Products/ZenRRD/utils.py (rpneval)
    rpn = ''

    # dpName:  The basename of the rrd file (without extension) that has the data
    dpName = ''

    # cFunc:   The consolidation function used when that datapoint resolution
    #          exceeds the graph.  See Products/ZenModel/RRDGraph dataSourceSum and
    #          http://oss.oetiker.ch/rrdtool/doc/rrdgraph_data.en.html
    cFunc = 'AVERAGE'

    #skipCalc: Flag used for disabling magnitude calculation in graphs footer
    skipCalc = False

    _properties = ComplexGraphPoint._properties + (
        {'id':'limit', 'type':'long', 'mode':'w'},
        {'id':'rpn', 'type':'string', 'mode':'w'},
        {'id':'dpName', 'type':'string', 'mode':'w'},
        {'id':'cFunc', 'type':'string', 'mode':'w'},
        {'id':'skipCalc', 'type':'boolean', 'mode':'w'},
        )

    def getDescription(self):
        ''' return a description
        '''
        return self.dpName


    def dataPointId(self):
        '''
        Return the id of the datapoint, without the datasource name
        '''
        return self.dpName.split('_', 1)[-1]


    def getType(self):
        return 'DataPoint'


    def isBroken(self):
        """
        If this graphpoint's graph definition is associated with a perf
        template and if the datapoint needed by this gp is not present in 
        the perf template then return True, otherwise false.
        """
        if self.graphDef.rrdTemplate():
            if self.dpName \
                    not in self.graphDef.rrdTemplate.getRRDDataPointNames():
                return True
        return False


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        graph = []

        rrdFile = os.path.join(rrdDir, self.dpName) + ".rrd"

        # Create the base DEF
        rawName = self.getDsName('%s-raw' % self.id, multiid, prefix)        
        graph.append("DEF:%s=%s:%s:%s" % (rawName, rrdFile, 'ds0', self.cFunc))

        # If have rpn then create a new CDEF
        if self.rpn:
            rpn = self.talesEval(self.rpn, context)
            rpnName = self.getDsName('%s-rpn' % self.id, multiid, prefix)
            graph.append("CDEF:%s=%s,%s" % (rpnName, rawName, rpn))

        # If have limit then create a new CDEF
        if self.limit > -1:
            src = self.rpn and rpnName or rawName
            limitName = self.getDsName('%s-limit' % self.id, multiid, prefix)
            graph.append("CDEF:%s=%s,%s,GT,UNKN,%s,IF"%
                        (limitName,src,self.limit,src))

        if self.limit > -1:
            src = limitName
        elif self.rpn:
            src = rpnName
        else:
            src = rawName

        # Create a cdef for the munged value        
        graph.append('CDEF:%s=%s' % 
                            (self.getDsName(self.id, multiid, prefix), src))

        # Draw
        if self.lineType != self.LINETYPE_DONTDRAW:
            if multiid != -1:
                fname = os.path.basename(rrdDir)
                if fname.find('.rrd') > -1: fname = fname[:-4]
                legend = "%s-%s" % (self.id, fname)
            else:
                legend = self.talesEval(self.legend, context) or self.id
            legend = self.escapeForRRD(legend)
            drawType = self.lineType
            if self.lineType == self.LINETYPE_LINE:
                drawType += str(self.lineWidth)
            drawCmd ='%s:%s%s' % (
                        drawType,
                        src,
                        self.getColor(idx))
            drawCmd += ':%s' % legend.ljust(14)
            if self.stacked:
                drawCmd += ':STACK'
            graph.append(drawCmd)
            
            # Add summary
            if addSummary:
                graph.extend(self._summary(src, self.format, ongraph=1))
        
        return cmds + graph


    def _summary(self, src, format="%5.2lf%s", ongraph=1):
        """Add the standard summary opts to a graph"""
        gopts = []
        funcs = ("LAST", "AVERAGE")
        tags = ("cur\:", "avg\:")
        for i in range(len(funcs)):
            label = "%s%s" % (tags[i], format or self.DEFAULT_FORMAT)
            gopts.append(self.summElement(src, funcs[i], label, ongraph))
        gopts[-1] += "\j"
        return gopts


    def summElement(self, src, function, format="%5.2lf%s", ongraph=1):
        """Make a single summary element"""
        if ongraph: opt = "GPRINT"
        else: opt = "PRINT"
        return ":".join((opt, src, function, format))

    
InitializeClass(DataPointGraphPoint)
