##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""VruleGraphPoint

Handles GraphPoints that define an rrd VRULE
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass
from Products.ZenUtils.deprecated import deprecated


@deprecated
def manage_addVruleGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = VruleGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class VruleGraphPoint(GraphPoint):

    meta_type = 'VruleGraphPoint'

    time = 0
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'time', 'type':'int', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )
    
    def getDescription(self):
        return '%s %s %s' % (self.time, self.color, self.legend)


    def getType(self):
        return 'VRULE'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, prefix, rrdDir)
        if not self.time:
            return cmds

        gopts = 'VRULE:%s%s' % (self.time, self.getColor(idx))
        if self.legend:
            legend = self.talesEval(self.legend, context)
            legend = self.escapeForRRD(legend)
            gopts += ':%s' % legend
        return cmds + [gopts]


InitializeClass(VruleGraphPoint)
