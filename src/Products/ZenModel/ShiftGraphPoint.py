##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ShiftGraphPoint

Handles GraphPoints that define an rrd SHIFT
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass
from Products.ZenUtils.deprecated import deprecated


@deprecated
def manage_addShiftGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = ShiftGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class ShiftGraphPoint(GraphPoint):

    meta_type = 'ShiftGraphPoint'
    rrdFile = None
    vname = ''
    offset = 0

    _properties = GraphPoint._properties + (
        {'id':'vname', 'type':'string', 'mode':'w'},
        {'id':'offset', 'type':'long', 'mode':'w'},
        )

    def getDescription(self):
        return '%s' % self.offset


    def getType(self):
        return 'SHIFT'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, rrdDir)
        if not (self.rrdFile and self.dsName and self.cFunc):
            return cmds
        
        offset = self.talesEval(self.offset, context)

        return cmds + ['SHIFT:%s:%s' % (
                            self.addPrefix(prefix, self.vname), offset or 0)]


InitializeClass(ShiftGraphPoint)
