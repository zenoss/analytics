##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""TickGraphPoint

Handles GraphPoints that define an rrd TICK
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass
from Products.ZenUtils.deprecated import deprecated


@deprecated
def manage_addTickGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = TickGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class TickGraphPoint(GraphPoint):

    meta_type = 'TickGraphPoint'

    vname = ''
    color = ''
    fraction = ''
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'vname', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'fraction', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )

    def getDescription(self):
        return '%s' % self.fraction


    def getType(self):
        return 'TICK'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, rrdDir)
        if not self.vname:
            return cmds

        legend = self.talesEval(self.legend, context)
        legend = self.escapeForRRD(legend)
        return cmds + ['TICK:%s%s%s%s' % (
                    self.addPrefix(prefix, self.vname),
                    self.getColor(idx),
                    self.fraction and ':%s' % self.fraction or '',
                    legend and ':%s' % legend or '')]


InitializeClass(TickGraphPoint)
