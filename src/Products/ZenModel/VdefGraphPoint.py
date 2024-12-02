##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""VdefGraphPoint

Handles GraphPoints that define an rrd VDEF
"""

from AccessControl.class_init import InitializeClass

from Products.ZenModel.RpnGraphPoint import RpnGraphPoint
from Products.ZenUtils.deprecated import deprecated

@deprecated
def manage_addVdefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = VdefGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class VdefGraphPoint(RpnGraphPoint):
    meta_type = 'VdefGraphPoint'


    def getType(self):
        return 'VDEF'
        

    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                            multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, prefix, rrdDir)
        if not self.rpn:
            return cmds
        rpn = self.talesEval(self.rpn, context)
        return cmds + ['VDEF:%s=%s' % (
                        self.getDsName(self.id, multiid, prefix),
                        self.getRpn(multiid, prefix))]


InitializeClass(VdefGraphPoint)
