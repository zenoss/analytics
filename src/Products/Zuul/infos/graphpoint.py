##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.infos import InfoBase, ProxyProperty
from zope.schema.vocabulary import SimpleVocabulary
from Products.Zuul.interfaces import graphpoint as graphPointInterfaces
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.ZenModel.ComplexGraphPoint import ComplexGraphPoint


def complexGraphLineTypeVocabulary(context):
    return SimpleVocabulary.fromItems(ComplexGraphPoint.lineTypeOptions)


class GraphPointInfo(InfoBase):
    """
    Base class for all of the graph point definitions
    """
    @property
    def newId(self):
        return self._object.id

    @property
    def type(self):
        return self._object.getType()

    @property
    def description(self):
        return self._object.getDescription()

    @property
    def rrdVariables(self):
        """
        Returns a list of all of the available RRD variables
        """
        # get the available variables from the graph definition
        graphDef = self._object.graphDef()
        variables = graphDef.getRRDVariables(self._object.sequence)

        # the old UI returned the string "None" if there were not any variables
        return variables or _t(u'None')


class ColorGraphPointInfo(GraphPointInfo):
    """
    Info object for color graph point
    """
    color = ProxyProperty('color')
    legend = ProxyProperty('legend')


class ThresholdGraphPointInfo(ColorGraphPointInfo):
    """
    Info object for threshold graph point
    """
    implements(graphPointInterfaces.IThresholdGraphPointInfo)


class DataPointGraphPointInfo(ColorGraphPointInfo):
    """
    Info object for the data point graph point
    """
    implements(graphPointInterfaces.IDataPointGraphPointInfo)
    lineType = ProxyProperty('lineType')
    lineWidth = ProxyProperty('lineWidth')
    stacked = ProxyProperty('stacked')
    format = ProxyProperty('format')
    limit = ProxyProperty('limit')
    rpn = ProxyProperty('rpn')
    dpName = ProxyProperty('dpName')
    cFunc = ProxyProperty('cFunc')
    skipCalc = ProxyProperty('skipCalc')


class DefGraphPointInfo(GraphPointInfo):
    """
    Info object for the Def Graph Point
    """
    implements(graphPointInterfaces.IDefGraphPointInfo)
    rrdFile = ProxyProperty('rrdFile')
    dsName = ProxyProperty('dsName')
    step = ProxyProperty('step')
    start = ProxyProperty('start')
    end = ProxyProperty('end')
    cFunc = ProxyProperty('cFunc')
    rFunc = ProxyProperty('rFunc')


class VdefGraphPointInfo(GraphPointInfo):
    """
    Info object for both the cdef and the vdef
    """
    implements(graphPointInterfaces.IVdefGraphPointInfo)
    rpn = ProxyProperty('rpn')


class PrintGraphPointInfo(GraphPointInfo):
    """
    Info Object for print graph points
    """
    implements(graphPointInterfaces.IPrintGraphPointInfo)
    vname = ProxyProperty('vname')
    format = ProxyProperty('format')
    strftime = ProxyProperty('strftime')


class CommentGraphPointInfo(GraphPointInfo):
    """
    Info Object for comment graph points
    """
    implements(graphPointInterfaces.ICommentGraphPointInfo)
    text = ProxyProperty('text')


class VruleGraphPointInfo(ColorGraphPointInfo):
    """
    Info Object for vrule graph points
    """
    implements(graphPointInterfaces.IVruleGraphPointInfo)
    time = ProxyProperty('time')


class HruleGraphPointInfo(ColorGraphPointInfo):
    """
    Info Object for Hrule graph points
    """
    implements(graphPointInterfaces.IHruleGraphPointInfo)
    value = ProxyProperty('value')


class LineGraphPointInfo(ColorGraphPointInfo):
    """
    Info Object for Line Graph Points
    """
    implements(graphPointInterfaces.ILineGraphPointInfo)
    lineWidth = ProxyProperty('lineWidth')
    stacked = ProxyProperty('stacked')
    value = ProxyProperty('value')


class AreaGraphPointInfo(ColorGraphPointInfo):
    """
    Info Object for Area Graph Points
    """
    implements(graphPointInterfaces.IAreaGraphPointInfo)
    stacked = ProxyProperty('stacked')
    value = ProxyProperty('value')


class TickGraphPointInfo(ColorGraphPointInfo):
    """
    Info Object for Tick Graph Points
    """
    implements(graphPointInterfaces.ITickGraphPointInfo)
    vname = ProxyProperty('vname')
    fraction = ProxyProperty('fraction')


class ShiftGraphPointInfo(GraphPointInfo):
    """
    Info Object for Shift Graph Points
    """
    implements(graphPointInterfaces.IShiftGraphPointInfo)
    vname = ProxyProperty('vname')
    offset = ProxyProperty('offset')
