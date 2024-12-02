##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""AreaGraphPoint

Handles GraphPoints that define an rrd AREA
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.Utils import unused

@deprecated
def manage_addAreaGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = AreaGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class AreaGraphPoint(GraphPoint):

    meta_type = 'AreaGraphPoint'

    value = ''
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND
    stacked = False

    _properties = GraphPoint._properties + (
        {'id':'value', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        )


    def getDescription(self):
        return '%s %s' % (self.value, self.legend)


    def getType(self):
        return 'AREA'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        unused(multiid, rrdDir)
        gopts = 'AREA:%s%s' % (
            self.addPrefix(prefix, self.value), self.getColor(idx))

        if self.legend or self.stacked:
            legend = self.talesEval(self.legend, context)
            legend = self.escapeForRRD(legend)
            gopts += ':%s' % legend
        if self.stacked:
            gopts += ':STACK'
        return cmds + [gopts]


InitializeClass(AreaGraphPoint)
