##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface
from Products.Zuul.interfaces import IInfo, IFacade
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class ITemplateNode(IInfo):
    """
    A template node contains template leaves. It contains all of the templates
    throughout device class hierarchy that share the same id.
    """


class ITemplateLeaf(IInfo):
    """
    A template leaf is a single instance of an RRD template at a specific
    spot in the device class hierarchy.
    """


class IRRDDataSourceInfo(IInfo):
    """
    Adapts RRDDatasource. This is distinct from the Basic DataSource
    because their properties are intermingled.
    This info exists so that if ZenPacks do not have a schema and descend from
    RRDDatasource then they will have this schema.

    See the _properties on the RRDDatasouce ZenModel
    """
    newId = schema.TextLine(title=_t(u'Name'),
                            xtype="idfield",
                            description=_t(u'The name of this datasource'))
    type = schema.TextLine(title=_t(u'Type'),
                           readonly=True)
    enabled = schema.Bool(title=_t(u'Enabled'))
    severity = schema.TextLine(title=_t(u'Severity'),
                               xtype='severity')
    eventKey = schema.TextLine(title=_t(u'Event Key'))
    eventClass = schema.TextLine(title=_t(u'Event Class'),
                                 xtype='eventclass')
    component = schema.TextLine(title=_t(u'Component'))


class IBasicDataSourceInfo(IInfo):
    """
    Adapts BasicDataSource (the common properties between SNMP and
    COMMAND infos)
    """
    newId = schema.TextLine(title=_t(u'Name'),
                            xtype="idfield",
                            description=_t(u'The name of this datasource'))
    type = schema.TextLine(title=_t(u'Type'),
                           readonly=True)
    enabled = schema.Bool(title=_t(u'Enabled'))
    severity = schema.TextLine(title=_t(u'Severity'),
                               xtype='severity')
    eventClass = schema.TextLine(title=_t(u'Event Class'),
                                 xtype='eventclass')
    cycletime = schema.TextLine(title=_t(u'Cycle Time (seconds)'))
    parser = schema.TextLine(title=_t(u'Parser'),
                             xtype='parser')


class ICommandDataSourceInfo(IBasicDataSourceInfo):
    """
    Adapts basic datasource infos of type CMD
    """
    usessh = schema.Bool(title=_t(u'Use SSH'))
    component = schema.TextLine(title=_t(u'Component'))
    eventKey = schema.TextLine(title=_t(u'Event Key'))
    commandTemplate = schema.Text(title=_t(u'Command Template'),
                                  xtype='twocolumntextarea')


class ISNMPDataSourceInfo(IInfo):
    """
    Adaps a basic Datasource of type SNMP
    """
    newId = schema.TextLine(title=_t(u'Name'),
                            xtype="idfield",
                            description=_t(u'The name of this datasource'))
    type = schema.TextLine(title=_t(u'Type'),
                           readonly=True)
    oid = schema.TextLine(title=_t(u'OID'))
    enabled = schema.Bool(title=_t(u'Enabled'))


class IPingDataSourceInfo(IRRDDataSourceInfo):
    cycleTime = schema.Int(title=_t(u'Cycle Time (seconds)'),
                           vtype='positive')
    eventClass = schema.TextLine(title=_t(u'Event Class'),
                                 xtype='eventclass', readonly=True)
    sampleSize = schema.Int(title=_t(u'Number of pings to send per cycle'),
                          vtype='positive')
    attempts = schema.Int(title=_t(u'Maximum ping retries'),
                          vtype='positive')


class IDataPointInfo(IInfo):
    """
    Adapts RRDDataPoint.
    """
    newId = schema.TextLine(title=_t(u'Name'),
                            xtype="idfield",
                            description=_t(u'The name of this data point'))
    description = schema.Text(title=_t(u'Description'),
                              description=_t(u'The description of this data point'))
    rrdtype = schema.TextLine(title=_t(u'Type'),
                              description=_t(u'The type of data point we have'),
                              xtype='rrdtype')
    createCmd = schema.Text(title=_t(u'Create Command'))
    rrdmin = schema.TextLine(title=_t(u'RRD Minimum'))
    rrdmax = schema.TextLine(title=_t(u'RRD Maximum'))
    aliases = schema.TextLine(title=_t(u'Alias'),
                              xtype='alias')


class IThresholdInfo(IInfo):
    """
    Adapts ThresholdClass.
    """
    newId = schema.TextLine(title=_t(u'Name'),
                            xtype="idfield",
                            order=1)
    type = schema.TextLine(title=_t(u'Type'),
                           readonly=True, order=2)
    dsnames = schema.List(title=_t(u'DataPoints'),
                          xtype='datapointitemselector', order=3)
    severity = schema.TextLine(title=_t(u'Severity'),
                               xtype='severity', order=4)
    enabled = schema.Bool(title=_t(u'Enabled'), order=5)
    eventClass = schema.TextLine(title=_t(u'Event Class'),
                                 xtype='eventclass', order=8)


class IMinMaxThresholdInfo(IThresholdInfo):
    """
    Adapts the MinMaxThresholdClass
    """
    minval = schema.TextLine(title=_t(u'Minimum Value'), order=6)
    maxval = schema.TextLine(title=u'Maximum Value', order=7)
    escalateCount = schema.Int(title=_t(u'Escalate Count'), order=9)

    description = schema.TextLine(title=u'Description', order=2)
    explanation = schema.TextLine(title=u'Explanation', order=2)
    resolution = schema.TextLine(title=u'Resolution', order=2)


class IDataPointAlias(IInfo):
    """
    Adapts the RRDDataPointAlias
    """


class IGraphInfo(IInfo):
    """
    Adapts GraphDefinition.
    """

class IMetricServiceGraphDefinition(Interface):
    """
    Adapts a graph definition for being sent over to the server
    """

class IMetricServiceGraphPoint(Interface):
    pass

class ITemplateFacade(IFacade):
    """
    A facade for monitoring templates.
    """

    def getTemplates():
        """
        Get all the monitoring templates in the system. This is used to fill
        out the tree view in the UI.
        """
    def getAddTemplateTargets():
        """
        Returns a list of targets for a new template
        """

    def addTemplate(id):
        """
        Add a new monitoring template to the dmd/Devices device class.
        """

    def deleteTemplate(uid):
        """
        Delete the monitoring template that is uniquely identified by the uid
        parameter.
        """

    def getDataSources(uid):
        """
        Return the data sources contained by the monitoring template uniquely
        identified by the uid parameter.
        """

    def getThresholds(uid):
        """
        Fetch the thresholds  contained by the monitoring template uniquely
        identified by the uid parameter.
        """

    def getThresholdTypes():
        """
        Get the available threshold types.  MinMaxThreshold comes from core,
        and the Holt Winters zenpack defines another type.  These are both
        subclasses of ThresholdClass.
        """

    def addThreshold(uid, thresholdType, thresholdId, dataPoints):
        """
        Add a threshold to the monitoring template uniquely identified by the
        uid parameter.
        """

    def removeThreshold(uid):
        """
        Delete the threshold uniquely identified by the uid parameter.
        """

    def getGraphs(uid):
        """
        Fetch the graph definitions associated with the monitoring template
        that is uniquely identified by the uid parameter.
        """

    def addDataPointToGraph(dataPointUid, graphUid):
        """
        Add data point to a graph.
        """

    def getCopyTargets(uid, query=''):
        """
        Get the device classes and devices that are candidates for having the
        monitoring template uniquely identified by uid copied to them. To be
        a viable target the object must not already have a template with the
        same ID defined on it, and the titleOrId must start with query
        (case-insensitvie match).
        """

    def copyTemplate(uid, targetUid):
        """
        Copy the monitoring template uniquely identified by the uid parameter
        to the device class or device uniquely identified by the targetUid
        parameter.
        """

    def addGraphDefinition(templateUid, graphDefinitionId):
        """
        Add a graph definition to the monitoring template uniquely identified
        by the templateUid parameter.
        """

    def deleteGraphDefinition(uid):
        """
        Delete the graph definition uniquely identified by the uid parameter.
        """

    def getGraphPoints(uid):
        """
        Fetch the graph points (data points, thresholds, and custom)
        associated with the GraphDefinition that is uniquely identified by the
        uid parameter.
        """

    def addThresholdToGraph(graphUid, thresholdUid):
        """
        Add the ThresholdClass uniquely identified by the thresholdUid
        parameter as a ThresholdGraphPoint on the GraphDefinition uniquely
        identified by the graphUid parameter.
        """

    def addCustomToGraph(graphUid, customId, customType):
        """
        Add a custom graph point to the GraphDefinition uniquely identified by
        the graphUid parameter.  The customType parameter must be one of the
        pythonClassNames returned by getGraphInstructionTypes.
        """

    def getGraphInstructionTypes():
        """
        Generates dictionaries containing the pythonClassName and label for
        the graph instruction types supported by RRDtool.

        More info at http://oss.oetiker.ch/rrdtool/doc/rrdgraph_graph.en.html
        """

    def setGraphPointSequence(uids):
        """
        Set the sequence of the graph points uniquely identified by the items
        in the uids paramter.
        """

    def getGraphDefinition(uid):
        """
        Get the GraphDefinition uniquely identified by the uid paramter.
        """

    def setGraphDefinition(uid, data):
        """
        Bind the values in the data parameter dictionary to the
        GraphDefinition that is uniquely identified by uid.
        """

    def setGraphDefinitionSequence(uids):
        """
        Set the sequence of the graph definitions uniquely identified by the
        items in the uids paramter.
        """
