##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Line

Handles GraphPoints that define an rrd LINE
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass
from Products.ZenUtils.deprecated import deprecated


@deprecated
def manage_addLineGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = LineGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class LineGraphPoint(GraphPoint):

    meta_type = 'LineGraphPoint'

    lineWidth = 1
    value = ''
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND
    stacked = False

    _properties = GraphPoint._properties + (
        {'id':'lineWidth', 'type':'long', 'mode':'w'},
        {'id':'value', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        )

    def getDescription(self):
        return '%s %s' % (self.value, self.legend)


    def getType(self):
        return 'LINE'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, rrdDir)
        value = self.addPrefix(prefix, self.value)
        gopts = 'LINE%s:%s%s' % (
            (self.lineWidth or ''), value, self.getColor(idx))

        if self.legend or self.stacked:
            legend = self.talesEval(self.legend, context)
            legend = self.escapeForRRD(legend)
            gopts += ':%s' % legend
        if self.stacked:
            gopts += ':STACK'
        return cmds + [gopts]


InitializeClass(LineGraphPoint)
