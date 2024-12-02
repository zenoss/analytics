##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.interfaces import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IGraphPointInfo(IInfo):
    """
    Adapts GraphPoint.
    """
    newId = schema.TextLine(title=_t(u'Name'),
                            required=True,
                            order=1)
    type = schema.TextLine(title=_t(u'Type'),
                           readonly=True,
                           order=2)
    # this should always appear last (hence the 999)
    rrdVariables = schema.TextLine(title=_t(u'Available RRD Variables'),
                                   order=999,
                                   xtype='multilinedisplayfield')


class IColorGraphPointInfo(IGraphPointInfo):
    """
    Abstract interface for every graph point that has a color field
    """
    color = schema.TextLine(title=_t('Color (Hex value RRGGBB)'),
                            vtype='hexnumber')
    legend = schema.TextLine(title=_t('Legend'))


class IThresholdGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts Threshold Graph Point Info
    """


class IDataPointGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts DataPoint GraphPoint.
    """
    lineType = schema.Choice(title=_t('Line Type'),
                             vocabulary='complexGraphLineType',
                             order=5)
    lineWidth = schema.TextLine(title=_t('Line Width'), order=6)
    stacked = schema.Bool(title=_t('Stacked'), order=7)
    skipCalc = schema.Bool(title=_t('Display full value in footer'), order=8)
    format = schema.TextLine(title=_t('Format'), order=9)
    dpName = schema.TextLine(title=_t('DataPoint'), readonly=True, order=3)
    rpn = schema.Text(title=_t('RPN'), order=10)
    limit = schema.Int(title=_t('Limit'), order=11)
    cFunc = schema.TextLine(title=_t('Consolidation'), order=12)


class IDefGraphPointInfo(IGraphPointInfo):
    """
    Adapts Def Graph Points
    """
    rrdFile = schema.TextLine(title=_t(u'RRD File'))
    dsName = schema.TextLine(title=_t(u'RRD Data Source'))
    cFunc = schema.TextLine(title=_t(u'Consolidation'))
    start = schema.TextLine(title=_t(u'Start'))
    end = schema.TextLine(title=_t(u'End'))
    step = schema.TextLine(title=_t(u'Step'))
    rFunc = schema.TextLine(title=_t(u'Reduce'))


class IVdefGraphPointInfo(IGraphPointInfo):
    """
    Adapts Vdef Graph Points
    """
    rpn = schema.Text(title=_t(u'RPN'))


class IPrintGraphPointInfo(IGraphPointInfo):
    """
    Adapts Print Graph Points
    """
    vname = schema.TextLine(title=_t(u'Vname'))
    format = schema.TextLine(title=_t(u'Format'))
    strftime = schema.TextLine(title=_t(u'Strftime'))


class ICommentGraphPointInfo(IGraphPointInfo):
    """
    Adapts Print Graph Points
    """
    text = schema.TextLine(title=_t(u'Text'))


class IVruleGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts VRule Graph Points
    """
    time = schema.Int(title=_t(u'Time'),
                      vtype='positive')


class IHruleGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts HRule Graph Points
    """
    value = schema.TextLine(title=_t(u'Value'))


class ILineGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts Line Graph Points
    """
    lineWidth = schema.Int(title=_t(u'Line Width'))
    stacked = schema.Bool(title=_t('Stacked'))
    value = schema.TextLine(title=_t(u'Value'))


class IAreaGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts HRule Graph Points
    """
    stacked = schema.Bool(title=_t('Stacked'))
    value = schema.TextLine(title=_t(u'Value'))


class ITickGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts Tick Graph Points
    """
    vname = schema.TextLine(title=_t(u'Vname'))
    fraction = schema.TextLine(title=_t(u'Fraction'))


class IShiftGraphPointInfo(IGraphPointInfo):
    """
    Adapts Shift Graph Points
    """
    vname = schema.TextLine(title=_t(u'Vname'))
    offset = schema.Int(title=_t(u'Offset'))

