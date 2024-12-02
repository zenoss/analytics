##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""GprintGraphPoint

Handles GraphPoints that define an rrd GPRINT
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass


def manage_addGprintGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = GprintGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class GprintGraphPoint(GraphPoint):

    meta_type = 'GprintGraphPoint'

    vname = ''
    format = ''
    strftime = ''

    _properties = GraphPoint._properties + (
        {'id':'vname', 'type':'string', 'mode':'w'},
        {'id':'format', 'type':'string', 'mode':'w'},
        {'id':'strftime', 'type':'string', 'mode':'w'},
        )


    def getDescription(self):
        return self.format


    def getType(self):
        return 'GPRINT'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, rrdDir)
        return cmds + ['GPRINT:%s:%s%s' % (
                    self.addPrefix(prefix, self.vname),
                    (self.format or self.DEFAULT_FORMAT).replace(':', '\:'),
                    self.strftime and ':%s' % self.strftime or '')]


InitializeClass(GprintGraphPoint)
