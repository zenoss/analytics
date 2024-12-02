##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""RRDGraph

RRDGraph defines the global options for an rrdtool graph.
"""

###########################################################################
#
# RRDGraph is deprecated.  GraphDefinition is now used in its place.
# RRDGraph.py can be removed from zenoss post 2.1
#
###########################################################################

import os
import re

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.ZenTales import talesEval

from ZenModelRM import ZenModelRM

def manage_addRRDGraph(context, id, REQUEST = None):
    """make a RRDGraph"""
    graph = RRDGraph(id)
    context._setObject(graph.id, graph)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')
                                     

addRRDGraph = DTMLFile('dtml/addRRDGraph',globals())


class RRDGraph(ZenModelRM):

    meta_type = 'RRDGraph'
   
    security = ClassSecurityInfo()

    dsnames = []
    sequence = 0
    height = 100
    width = 500
    threshmap = []
    units = ""
    log = False
    linewidth = 1
    base = False
    stacked = False
    summary = True
    miny = -1
    maxy = -1
    custom = ""
    hasSummary = True


    _properties = (
        {'id':'dsnames', 'type':'lines', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'height', 'type':'int', 'mode':'w'},
        {'id':'width', 'type':'int', 'mode':'w'},
        {'id':'units', 'type':'string', 'mode':'w'},
        {'id':'linewidth', 'type':'int', 'mode':'w'},
        {'id':'log', 'type':'boolean', 'mode':'w'},
        {'id':'base', 'type':'boolean', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        {'id':'summary', 'type':'boolean', 'mode':'w'},
        {'id':'miny', 'type':'int', 'mode':'w'},
        {'id':'maxy', 'type':'int', 'mode':'w'},
        {'id':'colors', 'type':'lines', 'mode':'w'},
        {'id':'custom', 'type':'text', 'mode':'w'},
        {'id':'hasSummary', 'type':'boolean', 'mode':'w'},
        )

    _relations =  (
        ("rrdTemplate", ToOne(ToManyCont,"Products.ZenModel.RRDTemplate", "graphs")),
        )

    colors = (
        '#00cc00', '#0000ff', '#00ffff', '#ff0000', 
        '#ff9900', '#cc0000', '#0000cc', '#0080c0',
        '#8080c0', '#ff0080', '#800080', '#0000a0',
        '#408080', '#808000', '#000000', '#00ff00',
        '#fb31fb', '#0080ff', '#ff8000', '#800000', 
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDGraph',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Graph'
            , 'action'        : 'editRRDGraph'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )
    
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDGraph, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def getGraphCmds(self, context, rrdfile, template):
        """build the graph opts for a single rrdfile"""
        cmds = self.graphsetup()
        if self.custom:
            cmds = self.buildCustomDS(cmds, rrdfile, template)
            res = talesEval("string:"+self.custom, context)
            cmds.extend(res.split("\n"))
            if self.hasSummary:
                 cmds = self.addSummary(cmds)
        else:
            cmds = self.buildDS(cmds, rrdfile, template, self.summary)
        cmds = self.thresholds(cmds, context, template)
        return cmds


    def graphsetup(self):
        """Setup global graph parameters.
        """
        gopts = ['-F', '-E']
        if self.height:
            gopts.append('--height=%d' % self.height)
        if self.width:
            gopts.append('--width=%d' % self.width)
        if self.log:
            gopts.append('--logarithmic')
        if self.maxy > -1:
            gopts.append('--upper-limit=%d' % self.maxy)
            gopts.append('--rigid')
        if self.miny > -1:
            gopts.append('--lower-limit=%d' % self.miny)
            gopts.append('--rigid')
        if self.units: 
            gopts.append('--vertical-label=%s' % self.units)
            if self.units == 'percentage':
                if not self.maxy > -1:
                    gopts.append('--upper-limit=100')
                if not self.miny > -1:
                    gopts.append('--lower-limit=0')
        if self.base:
            gopts.append('--base=1024')
        return gopts
       

    def buildCustomDS(self, gopts, rrdfile, template):
        """Build a list of DEF statements for the dsnames in this graph.
        Their variable name will be dsname.  These can then be used in a 
        custom statement.
        """
        for dsname in self.dsnames:
            dp = template.getRRDDataPoint(dsname)
            if dp is None: continue
            myfile = os.path.join(rrdfile, dp.name()) + ".rrd"
            gopts.append('DEF:%s=%s:ds0:AVERAGE' % (dp.name(), myfile))
        return gopts
            

    def buildDS(self, gopts, rrdfile, template, summary,multiid=-1):
        """Add commands to draw data sources in this graph.
        """
        for dsindex, dsname in enumerate(self.dsnames):
            dp = template.getRRDDataPoint(dsname)
            dp.setIndex(dsindex)
            defcolor = self.colors[dsindex]
            deftype = self.gettype(dsindex)
            gopts += dp.graphOpts(rrdfile, defcolor, deftype, summary, multiid)
        return gopts

    def thresholds(self, gopts, context, template):
        """Add the hrule commands for any thresholds in this graph.
        """
        self._v_threshidx = len(self.colors)
        threshs = []
        for thresh in template.thresholds():
            if not thresh.canGraph(self): continue
            for dsname in thresh.dsnames:
                if dsname in self.dsnames:
                    threshs.append(thresh)
                    break
        if threshs: gopts.append("COMMENT:Data Thresholds\j")
        for i, thresh in enumerate(threshs):
            t = thresh.createThresholdInstance(context)
            color = self.getthreshcolor()
            gopts = t.getGraphElements(template, context, gopts, 'thresh%d' %
                    i, color)
        import logging
        log = logging.getLogger("debug")
        log.error('%r', gopts)
        return gopts


    gelement = re.compile("^LINE|^AREA|^STACK", re.I).search
    def addSummary(self, gopts):
        """Add summary labels for all graphed elements in gopts.
        """
        vars = [o.split(":",2)[1].split("#")[0] for o in gopts if self.gelement(o)]

        pad = max([len(v) for v in vars] + [0])
        for var in vars: 
            gopts = self.dataSourceSum(gopts, var, pad=pad)
        return gopts
            

    def dataSourceSum(self, gopts, src, pad=0, format="%0.2lf%s", ongraph=1):
        """Add the standard summary opts to a graph for variable src.
        VDEF:src_last=src,LAST 
        GPRINT:src_last:cur\:%0.2lf%s 
        VDEF:src_avg=src,AVERAGE
        GPRINT:src_avg:avg\:%0.2lf%s
        VDEF:src_max=src,MAXIMUM 
        GPRINT:src_max:max\:%0.2lf%s\j
        """
        from Products.ZenUtils.Utils import unused
        unused(pad)
        funcs = (("cur\:", "LAST"), ("avg\:", "AVERAGE"), ("max\:", "MAXIMUM"))
        for tag, func in funcs:
            label = "%s%s" % (tag, format)
            #if pad: label = label.ljust(pad)
            vdef = "%s_%s" % (src,func.lower())
            gopts.append("VDEF:%s=%s,%s" % (vdef,src,func))
            opt = ongraph and "GPRINT" or "PRINT"
            gopts.append("%s:%s:%s" % (opt, vdef, label))
        gopts[-1] += "\j"
        return gopts
    

    def getthreshcolor(self):
        """get a threshold color by working backwards down the color list"""
        self._v_threshidx -= 1
        a= self.colors[self._v_threshidx]
        return a


    def gettype(self, idx):
        """Return the default graph type for a data source
        first is area rest are lines
        """
        if idx == 0:
            return "AREA"
        elif self.stacked:
            return "STACK"
        else:
            return "LINE%d" % self.linewidth

InitializeClass(RRDGraph)
