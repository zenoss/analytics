##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""GraphDefinition

GraphDefinition defines the global options for a graph.
"""

import sys
import string

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from ZenModelRM import ZenModelRM
from Products.ZenWidgets import messaging
from ZenPackable import ZenPackable
import logging
log = logging.getLogger("zen.Device")
from Acquisition import aq_base
from Products.ZenUtils.Utils import resequence
from Products.ZenUtils.deprecated import deprecated
from Products.ZenMessaging.audit import audit
from zope.interface import implements
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.Zuul.decorators import memoize

@deprecated
def manage_addGraphDefinition(context, id, REQUEST = None):
    """
    This is here so that Zope will let us copy/paste/rename graph points.
    """
    if REQUEST:
        messaging.IMessageSender(self).sendToBrowser(
            'Unsupported',
            'That operation is not supported.',
            priority=messaging.WARNING
        )
        context.callZenScreen(REQUEST)

class FakeContext:
    isFake = True
    def __init__(self, name):
        self.id = name
    def __getattr__(self, name):
        return FakeContext(name)
    def __call__(self, *unused, **ignored):
        return self
    def __getitem__(self, key):
        return FakeContext(key)
    def __str__(self):
        return self.id
    def __repr__(self):
        return self.id
    def device(self):
        return self
    def __nonzero__(self):
        return True
    def rrdPath(self):
        return 'rrdPath'
    def getRRDTemplates(self):
        return []

class GraphDefinition(ZenModelRM, ZenPackable):
    """
    GraphDefinition defines the global options for a graph.
    """
    implements(IGloballyIdentifiable)
    meta_type = 'GraphDefinition'

    height = 500
    width = 500
    units = ""
    log = False
    base = False
    #summary = True
    miny = -1
    maxy = -1
    custom = ""
    hasSummary = True
    sequence = 0
    autoscale = None
    ceiling = None
    description = ""
    graphType = ""

    _properties = (
        {'id':'height', 'type':'int', 'mode':'w'},
        {'id':'width', 'type':'int', 'mode':'w'},
        {'id':'units', 'type':'string', 'mode':'w'},
        {'id':'log', 'type':'boolean', 'mode':'w'},
        {'id':'base', 'type':'boolean', 'mode':'w'},
        {'id':'autoscale', 'type':'boolean', 'mode':'w'},
        #{'id':'summary', 'type':'boolean', 'mode':'w'},
        {'id':'miny', 'type':'int', 'mode':'w'},
        {'id':'ceiling', 'type':'int', 'mode':'w'},
        {'id':'maxy', 'type':'int', 'mode':'w'},
        {'id':'custom', 'type':'text', 'mode':'w'},
        {'id':'hasSummary', 'type':'boolean', 'mode':'w'},
        {'id':'sequence', 'type':'long', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        )

    _relations =  (
        ("rrdTemplate",
            ToOne(ToManyCont,"Products.ZenModel.RRDTemplate", "graphDefs")),
        ('report',
            ToOne(ToManyCont, 'Products.ZenModel.MultiGraphReport', 'graphDefs')),
        ('graphPoints',
            ToManyCont(ToOne, 'Products.ZenModel.GraphPoint', 'graphDef')),
        # Remove this relationship after version 2.1
        ('reportClass',
            ToOne(ToManyCont, 'Products.ZenModel.MultiGraphReportClass', 'graphDefs')),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = (
    {
        'immediate_view' : 'editGraphDefinition',
        'actions'        :
        (
            { 'id'            : 'edit'
            , 'name'          : 'Graph Definition'
            , 'action'        : 'editGraphDefinition'
            , 'permissions'   : ( Permissions.view, )
            },
            { 'id'            : 'editCustom'
            , 'name'          : 'Graph Custom Definition'
            , 'action'        : 'editCustGraphDefinition'
            , 'permissions'   : ( Permissions.view, )
            },
            { 'id'            : 'viewCommands'
            , 'name'          : 'Graph Commands'
            , 'action'        : 'viewGraphCommands'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    ## Basic stuff

    def __init__(self, id, title=None, buildRelations=True):
        super(GraphDefinition , self).__init__(id, title=title, buildRelations=buildRelations)
        self._title = title

    @property
    @memoize
    def title(self):
        # allow zenpacks to set a temporary title on the graph definition.
        # once we have it remove the _v_title attribute because even though it is
        # volatile the object might be in cache in a subsequent request
        if hasattr(self, "_v_title"):
            name = self._v_title
            del self._v_title
            return name
        return self._title or self.getId()

    @title.setter
    def title(self, title):
        self._title = title

    def getGraphPoints(self, includeThresholds=True):
        """ Return ordered list of graph points
        """
        gps = (gp for gp in self.graphPoints()
                if includeThresholds or not gp.isThreshold)
        def graphPointKey(a):
            try:
                return int(a.sequence)
            except ValueError:
                return sys.maxint
        return sorted(gps, key=graphPointKey)

    def getDescription(self):
        description = self.description
        descriptionLines = description.split("\n")
        # for zenpacks parse the comments out of the custom
        if self.custom and not description:
            lines = self.custom.split("\n")
            for line in lines:
                if line.startswith("COMMENT:"):
                    comment = line.replace("COMMENT:", "")
                    # make sure we don't add it twice
                    if not comment in descriptionLines:
                        description = description + ", " + comment
        return description

    def getThresholdGraphPoints(self):
        """ Get ordered list of threshold graph points
        """
        gps = [gp for gp in self.getGraphPoints() if gp.isThreshold]
        return gps


    def isThresholdGraphed(self, threshId):
        """ Return true if there is a thresholdgraphpoint with threshId=threshid
        """
        return any(gp.threshId == threshId
                        for gp in self.getThresholdGraphPoints())


    def isDataPointGraphed(self, dpName):
        """ Return true if there is at least one graphpoint with a dsName
        equal to dpName.
        """
        from DataPointGraphPoint import DataPointGraphPoint
        return any(isinstance(gp, DataPointGraphPoint) and gp.dpName == dpName
                        for gp in self.getGraphPoints(includeThresholds=False))

    ## GUI Support


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        if self.rrdTemplate():
            from RRDTemplate import crumbspath
            crumbs = super(GraphDefinition, self).breadCrumbs(terminator)
            return crumbspath(self.rrdTemplate(), crumbs, -2)
        return ZenModelRM.breadCrumbs(self, terminator)


    def checkValidId(self, id, prep_id = False):
        """Checks a valid id
        """
        # RRD docs say that limit on vnames is 255 characters and that
        # A-Za-z0-9_ are the valid characters.  Zenoss reserves - for it's own
        # use.  Limiting to 200 instead just to leave room for whatever.
        # http://oss.oetiker.ch/rrdtool/doc/rrdgraph_data.en.html
        if len(id) > 200:
            return 'GraphPoint names can not be longer than 200 characters.'
        allowed = set(string.ascii_letters + string.digits + '_')
        attempted = set(id)
        if not attempted.issubset(allowed):
            return 'Only letters, digits and underscores are allowed' + \
                    ' in GraphPoint names.'
        return ZenModelRM.checkValidId(self, id, prep_id)


    def getGraphPointDescriptions(self):
        return [gi.getDescription() for gi in self.graphPoints()]


    def getGraphPointsNames(self):
        """ Return list of graph point ids
        """
        return [gp.id for gp in self.getGraphPoints()]


    def getGraphPointNamesString(self):
        """
        Return a string that lists the names of the graphpoints used in this
        graph definition.  If this graph definition has a perf template then
        note in the string which graphpoints are broken (in that they refer
        to nonexistent datapoints.)
        """
        names = []
        for gp in self.getGraphPoints():
            if hasattr(aq_base(gp), 'isBroken') and gp.isBroken():
                names.append('%s(<span style="color: red">missing</span>)' %
                                                                    gp.id)
            else:
                names.append(gp.id)
        return ', '.join(names)


    def getGraphPointOptions(self):
        """ Used by dialog_addGraphPoint to construct the list of
        available graphpoint types.
        """
        return (('DefGraphPoint', 'DEF'),
                ('VdefGraphPoint', 'VDEF'),
                ('CdefGraphPoint', 'CDEF'),
                ('PrintGraphPoint', 'PRINT'),
                ('GprintGraphPoint', 'GPRINT'),
                ('CommentGraphPoint', 'COMMENT'),
                ('VruleGraphPoint', 'VRULE'),
                ('HruleGraphPoint', 'HRULE'),
                ('LineGraphPoint', 'LINE'),
                ('AreaGraphPoint', 'AREA'),
                ('TickGraphPoint', 'TICK'),
                ('ShiftGraphPoint', 'SHIFT'))


    def createGraphPoint(self, cls, newId):
        """ Create the graphpoint with the given id or something similar
        and add to self.graphPoints
        """
        def getUniqueId(container, base):
                ids = set(container.objectIds())
                new = base
                i = 2
                while new in ids:
                    new = '%s%s' % (base, i)
                    i += 1
                return new
        newId = getUniqueId(self.graphPoints, newId)
        gp = cls(newId)
        # Set sequence
        if gp.isThreshold:
            gp.sequence = -1
        else:
            gp.sequence = len(self.graphPoints())
        # Set legend for graph points on multigraph reports
        if self.report() and hasattr(gp, 'legend'):
            # For MultiGraphReports we use a fancier legend
            # to differentiate when you have multiple devices/graphpoints
            # on a single graph
            gp.legend = gp.DEFAULT_MULTIGRAPH_LEGEND
        self.graphPoints._setObject(gp.id, gp)
        gp = self.graphPoints._getOb(gp.id)
        if gp.sequence == -1:
            self.manage_resequenceGraphPoints()
        return gp


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addCustomGraphPoint')
    def manage_addCustomGraphPoint(self, new_id, flavor, REQUEST=None):
        """ Create a new graphpoint of the given class and id
        """
        exec 'import %s' % flavor
        cls = eval('%s.%s' % (flavor, flavor))
        gp = self.createGraphPoint(cls, new_id)
        if REQUEST:
            audit('UI.GraphDefinition.AddGraphPoint', self.id, graphPointType=flavor, graphPoint=gp.id)
            url = '%s/graphPoints/%s' % (self.getPrimaryUrlPath(), gp.id)
            REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return gp


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataPointGraphPoints')
    def manage_addDataPointGraphPoints(self, dpNames=None,
                                       includeThresholds=False,
                                       REQUEST=None):
        """ Create new graph points
        The migrate script graphDefinitions and friends depends on the first
        element in newGps being the DataPointGraphPoint when only one
        name is passed in dpNames.
        """
        if not dpNames:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No graph points were selected.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        else:
            from DataPointGraphPoint import DataPointGraphPoint
            newGps = []
            for dpName in dpNames:
                dpId = dpName.split('_', 1)[-1]
                gp = self.createGraphPoint(DataPointGraphPoint, dpId)
                gp.dpName = dpName
                newGps.append(gp)
            if includeThresholds:
                for dpName in dpNames:
                    newGps += self.addThresholdsForDataPoint(dpName)
            for gp in newGps:
                audit('UI.GraphDefinition.AddGraphPoint', self.id, graphPointType='DataPoint',
                      graphPoint=gp.id, includeThresholds=str(includeThresholds))
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Graph Points Added',
                    '%s graph point%s were added.' % (len(newGps),
                        len(newGps) > 1 and 's' or '')
                )
                return self.callZenScreen(REQUEST)
            return newGps


    def addThresholdsForDataPoint(self, dpName):
        """ Make sure that Threshold graph points exist for all thresholds
        that use the given dpName.
        Return a list of all graphpoints created by this call.
        """
        from ThresholdGraphPoint import ThresholdGraphPoint
        newGps = []
        for thresh in self.rrdTemplate().thresholds():
            if thresh.canGraph(self) \
                    and dpName in thresh.dsnames \
                    and not self.isThresholdGraphed(thresh.id):
                gp = self.createGraphPoint(ThresholdGraphPoint, thresh.id)
                gp.threshId = thresh.id
                newGps.append(gp)
        return newGps


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addThresholdGraphPoints')
    def manage_addThresholdGraphPoints(self, threshNames, REQUEST=None):
        """ Create new threshold graph points
        """
        from ThresholdGraphPoint import ThresholdGraphPoint
        newGps = []
        for threshName in threshNames:
            #thresh = getattr(self.rrdTemplate.thresholds, threshName)
            gp = self.createGraphPoint(ThresholdGraphPoint, threshName)
            gp.threshId = threshName
            newGps.append(gp)
        if REQUEST:
            for threshName in threshNames:
                audit('UI.GraphDefinition.AddGraphPoint', self.id, graphPointType='Threshold',
                      graphPoint=threshName)
            messaging.IMessageSender(self).sendToBrowser(
                'Graph Points Added',
                '%s graph point%s were added.' % (len(newGps),
                    len(newGps) > 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)
        return newGps


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteGraphPoints')
    def manage_deleteGraphPoints(self, ids=(), REQUEST=None):
        """ Deleted given graphpoints
        """
        num = 0
        for id in ids:
            if getattr(self.graphPoints, id, False):
                num += 1
                self.graphPoints._delObject(id)
            self.manage_resequenceGraphPoints()
        if REQUEST:
            for id in ids:
                audit('UI.GraphDefinition.DeleteGraphPoint', self.id, graphPoint=id)
            messaging.IMessageSender(self).sendToBrowser(
                'Graph Points Deleted',
                '%s graph point%s were deleted.' % (num,
                    num > 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_resequenceGraphPoints')
    def manage_resequenceGraphPoints(self, seqmap=(), origseq=(), REQUEST=None):
        """Reorder the sequence of the GraphPoints.
        """
        retval = resequence(self, self.graphPoints(), seqmap, origseq, REQUEST)
        if REQUEST:
            audit('UI.GraphDefinition.ResequenceGraphPoints', self.id, sequence=seqmap, oldData_={'sequence':origseq})
        return retval


    def getDataPointOptions(self):
        """ Return a list of (value, name) tuples for the list of datapoints
        which the user selects from to create new graphpoints.
        """
        return [(dp.name(), dp.name())
                    for dp in self.rrdTemplate.getRRDDataPoints()]


    def getThresholdOptions(self):
        """ Return a list of (value, name) tuples for the list of thresholds
        which the user selects from to create new graphpoints.
        """
        return [(t.id, t.id) for t in self.rrdTemplate.thresholds()]


    ## Graphing Support


    def getGraphCmds(self, context, rrdDir, multiid=-1, upToPoint=None,
            includeSetup=True, includeThresholds=True,
            prefix='', cmds=None, idxOffset=0):
        """build the graph opts for a single rrdfile"""
        from Products.ZenUtils.ZenTales import talesEval
        if not cmds:
            cmds = []
        if includeSetup:
            cmds += self.graphsetup()

        # Have to draw thresholds before data so that thresholds won't
        # obscure data (especially if threshold uses TICK)
        if includeThresholds:
            threshGps = [gp for gp in self.getThresholdGraphPoints()
                        if upToPoint is None or gp.sequence < upToPoint]
            if threshGps:
                for index, gp in enumerate(threshGps):
                    try:
                        cmds = gp.getGraphCmds(cmds, context, rrdDir,
                                        self.hasSummary, index+idxOffset,
                                        multiid, prefix)
                    except (KeyError, NameError) as e:
                        cmds.append('COMMENT: UNKNOWN VALUE IN '
                            'GRAPHPOINT %s\: %s' % (gp.id, str(e)))
        gpList = [gp for gp in self.getGraphPoints(includeThresholds=False)
                    if upToPoint is None or gp.sequence < upToPoint]
        for index, gp in enumerate(gpList):
            try:
                cmds = gp.getGraphCmds(cmds, context, rrdDir,
                                        self.hasSummary, index+idxOffset,
                                        multiid, prefix)
            except (KeyError, NameError) as e:
                cmds.append('COMMENT: UNKNOWN VALUE IN GRAPHPOINT '
                        '%s\: %s' % (gp.id, str(e)))
        if self.custom and includeSetup and not upToPoint:
            try:
                res = talesEval("string:"+str(self.custom), context)
            except (KeyError, NameError) as e:
                res = 'COMMENT:UNKNOWN VALUE IN CUSTOM COMMANDS\: %s' % str(e)
            cmds.extend(l for l in res.split('\n') if l.strip())
            #if self.hasSummary:
            #    cmds = self.addSummary(cmds)

        return cmds


    def getRRDVariables(self, upToPoint=None):
        """ Return list of rrd variable names that are defined by DEF, CDEF
        or VDEF statements in the rrd commands.  If upToPoint is not None then
        only consider statements generated by graphoints where
        sequence < upToPoint
        """
        cmds = self.getFakeGraphCmds(upToPoint=upToPoint)
        names = [line[line.find(':')+1:line.find('=')]
                    for line in cmds.split('\n')
                    if line[:line.find(':')] in ('DEF', 'CDEF', 'VDEF')]
        nameSet = set(names)
        result = []
        for name in names:
            #only allow -raw variables if a corresponding -rpn variable is present
            if name.endswith('-raw') and name.replace('-raw', '-rpn') in nameSet or not name.endswith('-raw'):
                result.append(name)
        return result


    def getFakeGraphCmds(self, upToPoint=None):
        """ Used to display the graph commands (or a reasonable likeness)
        to the user
        """
        context = FakeContext('Context')
        cmds = self.getGraphCmds(context, context.rrdPath(), upToPoint=upToPoint)
        cmds = '\n'.join(cmds)
        return cmds


    def graphsetup(self):
        """Setup global graph parameters.
        """
        gopts = ['-F', '-E', '--disable-rrdtool-tag']
        if self.height:
            gopts.append('--height=%d' % int(self.height))
        if self.width:
            gopts.append('--width=%d' % int(self.width))
        if self.log:
            gopts.append('--logarithmic')
        if self.maxy > -1:
            gopts.append('--upper-limit=%d' % int(self.maxy))
            gopts.append('--rigid')
        if self.miny > -1:
            gopts.append('--lower-limit=%d' % int(self.miny))
            gopts.append('--rigid')
        # Always include a vertical label so that multiple graphs on page
        # align correctly.
        gopts.append('--vertical-label=%s' % (self.units or ' '))
        if self.units == 'percentage':
            if not self.maxy > -1:
                gopts.append('--upper-limit=100')
            if not self.miny > -1:
                gopts.append('--lower-limit=0')
        if self.base:
            gopts.append('--base=1024')
        gopts = [str(o) for o in gopts]
        return gopts


    def getDataPointGraphPoints(self, dpName):
        """ Return a list of DataPointGraphPoints that use the given dpName
        """
        from DataPointGraphPoint import DataPointGraphPoint
        return [gp for gp in self.graphPoints()
                if isinstance(gp, DataPointGraphPoint)
                and gp.dpName == dpName]

    def shouldAutoScale(self):
        """
        Returns if we should scale the values down (i.e. convert bytes to megabytes)
        """
        if self.autoscale is not None:
            return self.autoscale
        # preserve backwards compatability for zenpacks
        for dp in self.graphPoints():
            if dp.meta_type == 'DataPointGraphPoint' and dp.shouldAutoScale():
                return True
        return False

    def getCeiling(self):
        """
        Returns how many digits should be displayed on the left hand
        side of the chart
        """
        if self.ceiling is not None:
            return self.ceiling
        # preserve backwards compatability for zenpacks
        for dp in self.graphPoints():
            if dp.meta_type == 'DataPointGraphPoint' and dp.format:
                try:
                    lhs = dp.format.split(".")[0][-1]
                    rhs = dp.format.split(".")[1][0]
                    return int(lhs) - int(rhs)
                except (IndexError, ValueError, TypeError):
                    # unable to parse the format just continue
                    # or use the default
                    pass
        return 3

    def getUniqueDpNames(self, limit=None):
        """
        Get a list of all unique datapoint names
        """
        dpNames = set()
        limitReached = False
        for t in self.dmd.Devices.getAllRRDTemplates():
            for ds in t.datasources():
                # If we have a broken datasource (likely from a missing zenpack)
                # then don't try to parse datapoints, you can't.
                if hasattr(ds, 'datapoints'):
                    for dp in ds.datapoints():
                        dpNames.add(dp.name())
                        if limit and len(dpNames) >= limit:
                            limitReached = True
                            break
                if limitReached:
                    break
            if limitReached:
                break
        return sorted(dpNames)


    def getUniqueThresholdNames(self, limit=100):
        """
        Get a list of all unique threshold names
        """
        names = set()
        limitReached = False
        for t in self.dmd.Devices.getAllRRDTemplates():
            for thresh in t.thresholds():
                names.add(thresh.id)
                if len(names) >= limit:
                    limitReached = True
                    break
            if limitReached:
                break
        return sorted(names)


InitializeClass(GraphDefinition)
