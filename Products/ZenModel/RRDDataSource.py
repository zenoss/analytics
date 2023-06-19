##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenUtils.path import binPath

__doc__="""RRDDataSource

Base class for DataSources
"""

import inspect
import os
import zope.component

from DateTime import DateTime
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD

from Products.PageTemplates.Expressions import getEngine

from Products.ZenUtils.ZenTales import talesCompile, talesEvalStr
from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets import messaging

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


class RRDDataSource(ZenModelRM, ZenPackable):

    meta_type = 'RRDDataSource'

    paramtypes = ('integer', 'string', 'float')
    sourcetypes = ()
    
    sourcetype = None
    enabled = True
    component = ''
    eventClass = ''
    eventKey = ''
    severity = 3
    commandTemplate = ""
    cycletime = '${here/zCommandCollectionInterval}'

    _properties = (
        {'id':'sourcetype', 'type':'selection',
        'select_variable' : 'sourcetypes', 'mode':'w'},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'component', 'type':'string', 'mode':'w'},
        {'id':'eventClass', 'type':'string', 'mode':'w'},
        {'id':'eventKey', 'type':'string', 'mode':'w'},
        {'id':'severity', 'type':'int', 'mode':'w'},
        {'id':'commandTemplate', 'type':'string', 'mode':'w'},
        {'id':'cycletime', 'type':'string', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("rrdTemplate", ToOne(ToManyCont,"Products.ZenModel.RRDTemplate","datasources")),
        ("datapoints", ToManyCont(ToOne,"Products.ZenModel.RRDDataPoint","datasource")),
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Source'
            , 'action'        : 'editRRDDataSource'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    
    def talesEval(self, text, context):
        if text is None:
            return

        device = context.device()
        extra = {
            'device': device,
            'dev': device,
            'devname': device.id,
            'datasource': self,
            'ds': self,
        }

        return talesEvalStr(str(text), context, extra=extra)


    def getCycleTime(self, context):
        return int(self.talesEval(self.cycletime, context))
        

    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDDataSource, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def getDescription(self):
        return None


    def getRRDDataPoints(self):
        return self.datapoints()
        
        
    def useZenCommand(self):
        return False

    def addDataPoints(self):
        """Abstract hook method, to be overridden in derived classes."""
        pass

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addRRDDataPoint')
    def manage_addRRDDataPoint(self, id, REQUEST = None):
        """make a RRDDataPoint"""
        if not id:
            return self.callZenScreen(REQUEST)
        from Products.ZenModel.RRDDataPoint import RRDDataPoint
        dp = RRDDataPoint(id)
        self.datapoints._setObject(dp.id, dp)
        dp = self.datapoints._getOb(dp.id)
        if REQUEST:
            if dp:
                url = '%s/datapoints/%s' % (self.getPrimaryUrlPath(), dp.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return dp


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteRRDDataPoints')
    def manage_deleteRRDDataPoints(self, ids=(), REQUEST=None):
        """Delete RRDDataPoints from this RRDDataSource"""

        def clean(rel, id):
            for obj in rel():
                if id in obj.dsnames:
                    obj.dsnames.remove(id)
                    if not obj.dsnames:
                        rel._delObject(obj.id)

        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            dp = getattr(self.datapoints,id,False)
            if dp:
                clean(self.graphs, dp.name())
                clean(self.thresholds, dp.name())
                self.datapoints._delObject(dp.id)
                
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataPointsToGraphs')
    def manage_addDataPointsToGraphs(self, ids=(), graphIds=(), REQUEST=None):
        """
        Create GraphPoints for all datapoints given datapoints (ids)
        in each of the graphDefs (graphIds.)
        If a graphpoint already exists for a datapoint in a graphDef then
        don't create a 2nd one.
        """
        newGps = []
        for graphDefId in graphIds:
            graphDef = self.rrdTemplate.graphDefs._getOb(graphDefId, None)
            if graphDef:
                for dpId in ids:
                    dp = self.datapoints._getOb(dpId, None)
                    if dp and not graphDef.isDataPointGraphed(dp.name()):
                        newGps += graphDef.manage_addDataPointGraphPoints(
                                                                [dp.name()])
        if REQUEST:
            numNew = len(newGps)
            messaging.IMessageSender(self).sendToBrowser(
                'Graph Points Added',
                '%s GraphPoint%s added' % (numNew, numNew != 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)
        return newGps


    def getCommand(self, context, cmd=None, device=None):
        """Return localized command target.
        """
        # Perform a TALES eval on the expression using self
        if cmd is None:
            cmd = self.commandTemplate
        if not cmd.startswith('string:') and not cmd.startswith('python:'):
            cmd = 'string:%s' % cmd
        compiled = talesCompile(cmd)
        d = device if device is not None else context.device()
        environ = {'dev' : d,
                   'device': d,
                   'devname': d.id,
                   'ds': self,
                   'datasource': self,
                   'here' : context,
                   'context': context,
                   'zCommandPath' : context.zCommandPath,
                   'nothing' : None,
                   'now' : DateTime() }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        res = self.checkCommandPrefix(context, res)
        return res
        

    def getComponent(self, context, component=None, device=None):
        """Return localized component.
        """
        if component is None:
            component = self.component
        if not component.startswith('string:') and \
                not component.startswith('python:'):
            component = 'string:%s' % component
        compiled = talesCompile(component)
        d = device if device is not None else context.device()
        environ = {'dev' : d,
                   'device': d,
                   'devname': d.id,
                   'here' : context,
                   'context' : context,
                   'nothing' : None,
                   'now' : DateTime() }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        return res

    def checkCommandPrefix(self, context, cmd):
        if not cmd.startswith('/') and not cmd.startswith('$'):
            if context.zCommandPath and not cmd.startswith(context.zCommandPath):
                cmd = os.path.join(context.zCommandPath, cmd)
            elif binPath(cmd.split(" ",1)[0]):
                #if we get here it is because cmd is not absolute, doesn't
                #start with $, zCommandPath is not set and we found cmd in
                #one of the zenoss bin dirs
                cmdList = cmd.split(" ",1) #split into command and args
                cmd = binPath(cmdList[0])
                if len(cmdList) > 1:
                    cmd = "%s %s" % (cmd, cmdList[1])
                
        return cmd

    def testDataSourceAgainstDevice(self, testDevice, REQUEST, write, errorLog):
        """
        Does the majority of the logic for testing a datasource against the device
        @param string testDevice The id of the device we are testing
        @param Dict REQUEST the browers request
        @param Function write The output method we are using to stream the result of the command
        @parma Function errorLog The output method we are using to report errors
        """
        device = None
        if testDevice:
            # Try to get specified device
            device = self.findDevice(testDevice)
            if not device:
                errorLog(
                    'No device found',
                    'Cannot find device matching %s.' % testDevice)
                return self.callZenScreen(REQUEST)
        elif hasattr(self, 'device'):
            # ds defined on a device, use that device
            device = self.device()
        if not device:
            errorLog(
                'No Testable Device',
                'Cannot determine a device against which to test.')
            return self.callZenScreen(REQUEST)
        device.monitorPerDatasource(self, REQUEST, write)

    def getSeverityString(self):
        return self.ZenEventManager.getSeverityString(self.severity)


    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None, ignored=None):
        return ZenModelRM.zmanage_editProperties(self, REQUEST)


class SimpleRRDDataSource(RRDDataSource):
    """
    A SimpleRRDDataSource has a single datapoint that shares the name of the 
    data source.
    """
    security = ClassSecurityInfo()
    
    
    security.declareProtected(ZEN_MANAGE_DMD, 'addDataPoints')
    def addDataPoints(self):
        """
        Make sure there is exactly one datapoint and that it has the same name
        as the datasource.
        """
        dpid = self.prepId(self.id)
        remove = [d for d in self.datapoints() if d.id != dpid]
        for dp in remove:
            self.datapoints._delObject(dp.id)
        if not self.datapoints._getOb(dpid, None):
            self.manage_addRRDDataPoint(dpid)

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        """
        Overrides the method defined in RRDDataSource. Called when user clicks
        the Save button on the Data Source editor page.
        """
        self.addDataPoints()

        if REQUEST and self.datapoints():

            datapoint = self.soleDataPoint()

            if REQUEST.has_key('rrdtype'):
                if REQUEST['rrdtype'] in datapoint.rrdtypes:
                    datapoint.rrdtype = REQUEST['rrdtype']
                else:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        "%s is an invalid Type" % rrdtype,
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)

            if REQUEST.has_key('rrdmin'):
                value = REQUEST['rrdmin']
                if value != '': 
                    try:
                        value = long(value)
                    except ValueError:
                        messaging.IMessageSender(self).sendToBrowser(
                            'Error',
                            "%s is an invalid RRD Min" % value,
                            priority=messaging.WARNING
                        )
                        return self.callZenScreen(REQUEST)
                datapoint.rrdmin = value

            if REQUEST.has_key('rrdmax'):
                value = REQUEST['rrdmax']
                if value != '': 
                    try:
                        value = long(value)
                    except ValueError:
                        messaging.IMessageSender(self).sendToBrowser(
                            'Error',
                            "%s is an invalid RRD Max" % value,
                            priority=messaging.WARNING
                        )
                        return self.callZenScreen(REQUEST)
                datapoint.rrdmax = value

            if REQUEST.has_key('createCmd'):
                datapoint.createCmd = REQUEST['createCmd']

        return RRDDataSource.zmanage_editProperties(self, REQUEST)

    def soleDataPoint(self):
        """
        Return the datasource's only datapoint
        """
        dps = self.datapoints()
        if dps:
            return dps[0]

    def aliases(self):
        """
        Return the datapoint aliases that belong to the datasource's only
        datapoint
        """
        dp = self.soleDataPoint()
        if dp:
            return dp.aliases()

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataPointsToGraphs')
    def manage_addDataPointsToGraphs(self, ids=(), graphIds=(), REQUEST=None):
        """
        Override method in super class.  ids will always be an empty tuple, so
        call the super class's method with the single datapoint as the ids.
        """
        return RRDDataSource.manage_addDataPointsToGraphs(self,
                (self.soleDataPoint().id,), graphIds, REQUEST)
    
    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataPointAlias')
    def manage_addDataPointAlias(self, id, formula, REQUEST=None):
        """
        Add a datapoint alias to the datasource's only datapoint
        """
        alias = self.soleDataPoint().manage_addDataPointAlias( id, formula )
        if REQUEST:
            return self.callZenScreen( REQUEST )
        return alias

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_removeDataPointAliases')
    def manage_removeDataPointAliases(self, ids=(), REQUEST=None):
        """
        Remove the passed aliases from the datasource's only datapoint
        """
        self.soleDataPoint().manage_removeDataPointAliases( ids )
        if REQUEST:
            return self.callZenScreen(REQUEST)

from Products.ZenModel.interfaces import IZenDocProvider
from Products.ZenModel.ZenModelBase import ZenModelZenDocProvider

class SimpleRRDDataSourceZenDocProvider(ZenModelZenDocProvider):
    zope.component.adapts(SimpleRRDDataSource)

    def datapoints(self):
        return self._underlyingObject.datapoints()

    def soleDataPoint(self):
        return self._underlyingObject.soleDataPoint()
    
    def getZendoc(self):
        if len( self.datapoints() ) == 1:
            dataPointAdapter = zope.component.queryAdapter( self.soleDataPoint(),
                                                            IZenDocProvider )
            return dataPointAdapter.getZendoc()
        else:
            return super( SimpleRRDDataSourceZenDocProvider, self ).getZendoc()

    def setZendoc(self, zendocText):
        """Set zendoc text"""
        if len( self.datapoints() ) == 1:
            dataPointAdapter = zope.component.queryAdapter( self.soleDataPoint(),
                                                            IZenDocProvider )
            dataPointAdapter.setZendoc( zendocText )
        else:
            return super( SimpleRRDDataSourceZenDocProvider, self ).setZendoc( zendocText )


def isPythonDataSource(ds):
    """Returns True if the RRDDataSource's sourcetype is Python (or derived).
    """
    if ds.sourcetype == "Python":
        return True
    return any(
        cls.sourcetype == "Python"
        for cls in inspect.getmro(ds.__class__)
        if hasattr(cls, "sourcetype")
    )
