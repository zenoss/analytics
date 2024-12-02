##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""CdefGraphPoint

Handles GraphPoints that define an rrd CDEF
"""

from AccessControl.class_init import InitializeClass

from Products.ZenModel.RpnGraphPoint import RpnGraphPoint


def manage_addCdefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = CdefGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class CdefGraphPoint(RpnGraphPoint):
    meta_type = 'CdefGraphPoint'


    def getType(self):
        return 'CDEF'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx,
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(rrdDir)
        if not self.rpn:
            return cmds
        rpn = self.talesEval(self.rpn, context)
        return cmds + ['CDEF:%s=%s' % (
                        self.getDsName(self.id, multiid, prefix),
                        self.getRpn(multiid, prefix))]


InitializeClass(CdefGraphPoint)
