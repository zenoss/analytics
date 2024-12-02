##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ComplexGraphPoint
"""

from GraphPoint import GraphPoint                                     
from AccessControl.class_init import InitializeClass


class ComplexGraphPoint(GraphPoint):

    LINETYPE_DONTDRAW = 'DONTDRAW'
    LINETYPE_LINE = 'LINE'
    LINETYPE_AREA = 'AREA'

    lineTypeOptions = (
        ('Not Drawn', LINETYPE_DONTDRAW),
        ('Line', LINETYPE_LINE),
        ('Area', LINETYPE_AREA),
        )

    color = ''
    lineType = LINETYPE_LINE
    lineWidth = 1
    stacked = False
    format = GraphPoint.DEFAULT_FORMAT
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'lineType', 'type':'selection', 
        'select_variable' : 'lineTypes', 'mode':'w'},
        {'id':'lineWidth', 'type':'long', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        {'id':'format', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )
    
    def shouldAutoScale(self):
        return "%s" in self.format


InitializeClass(ComplexGraphPoint)
