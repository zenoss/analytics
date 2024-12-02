##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""CommentGraphPoint

Handles GraphPoints that define an rrd COMMENT
"""

from GraphPoint import GraphPoint
from AccessControl.class_init import InitializeClass

def manage_addCommentGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = CommentGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class CommentGraphPoint(GraphPoint):

    meta_type = 'CommentGraphPoint'

    text = ''

    _properties = GraphPoint._properties + (
        {'id':'text', 'type':'string', 'mode':'w'},
        )

    def getDescription(self):
        return self.text


    def getType(self):
        return 'COMMENT'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(cmds, context, rrdDir, addSummary, idx, multiid, prefix)
        return cmds + ['COMMENT:%s' % self.text.replace(':', '\:')]


InitializeClass(CommentGraphPoint)
