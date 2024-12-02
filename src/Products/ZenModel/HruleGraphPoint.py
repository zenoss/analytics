##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__=""" 

Handles GraphPoints that define an rrd Line
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass


def manage_addHruleGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = HruleGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class HruleGraphPoint(GraphPoint):

    meta_type = 'HruleGraphPoint'

    value = ''
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'value', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )
    

    def getDescription(self):
        return '%s %s' % (self.value, self.color)


    def getType(self):
        return 'HRULE'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, prefix, rrdDir)
        legend = self.talesEval(self.legend, context)
        legend = self.escapeForRRD(legend)
        return cmds + ['HRULE:%s%s%s' % (
                    self.value or 0,
                    self.getColor(idx),
                    legend and ':%s' % legend or '')]


InitializeClass(HruleGraphPoint)
